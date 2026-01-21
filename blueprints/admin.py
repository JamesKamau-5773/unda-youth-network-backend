from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app, abort
import threading
from flask_login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from models import db, Champion, YouthSupport, RefferalPathway, TrainingRecord, get_champions_needing_refresher, get_high_risk_champions, get_overdue_reviews, User, MemberRegistration, ChampionApplication, Podcast, Event, DailyAffirmation, SymbolicItem, MentalHealthAssessment, MediaGallery, InstitutionalToolkitItem, UMVGlobalEntry, ResourceItem, BlogPost
from decorators import admin_required
from flask_bcrypt import Bcrypt
import secrets
import string
from datetime import datetime, timedelta, timezone
from services import user_service, champion_service, mailer, registration_service, champion_application_service, assignment_service, event_service, affirmation_service, media_gallery_service, toolkit_service, resource_service, story_service, symbolic_item_service, umv_service, assessment_service, podcast_service
from services.admin_metrics import get_dashboard_metrics
from dataclasses import asdict
from extensions import limiter
import json
import re


def slugify(value: str) -> str:
    value = (value or '').strip().lower()
    # replace non-alphanumeric characters with hyphens
    value = re.sub(r'[^a-z0-9]+', '-', value)
    value = re.sub(r'(^-|-$)+', '', value)
    return value

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Pages we track for personalization (id, display name, endpoint)
TRACKABLE_ADMIN_PAGES = {
    'admin.podcasts': ('podcasts', 'Manage Podcasts'),
    'admin.workstreams': ('workstreams', 'Workstreams'),
    'admin.affirmations': ('affirmations', 'Daily Affirmations'),
    'admin.list_media_galleries': ('media_galleries', 'Media Galleries'),
    'admin.list_toolkit_items': ('institutional_toolkit', 'Institutional Toolkit'),
    'admin.list_resources': ('resources', 'Resources'),
    'admin.list_stories': ('stories', 'Success Stories'),
    'admin.manage_users': ('manage_users', 'Manage Users'),
    'admin.debates': ('debators_circle', 'Debators Circle')
}


@admin_bp.before_app_request
def _record_admin_visit():
    # Only track GET page loads in admin blueprint for authenticated users
    try:
        if request.blueprint != 'admin':
            return
        if request.method != 'GET':
            return
        if not current_user or not current_user.is_authenticated:
            return

        endpoint = request.endpoint
        if not endpoint:
            return

        mapping = TRACKABLE_ADMIN_PAGES.get(endpoint)
        if not mapping:
            return

        page_id, display_name = mapping
        # Update user's frequent pages (non-blocking)
        try:
            current_user.touch_frequent_page(page_id, display_name, endpoint)
        except Exception:
            # Swallow errors - tracking must not break UI
            current_app.logger.debug('Failed to update frequent_pages for user')
    except Exception:
        # Defensive: ensure nothing leaks through
        return


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    metrics = get_dashboard_metrics()
    # Use asdict() to convert dataclass to mapping for template rendering
    return render_template('admin/dashboard.html', **asdict(metrics))


@admin_bp.route('/settings')
@login_required
@admin_required
def settings():
    """User profile and account settings"""
    return render_template('admin/settings.html', user=current_user)


@admin_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
@admin_required
def change_password():
    """Allow any user to change their own password"""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Basic form validation
        if not current_password or not new_password or not confirm_password:
            flash('All fields are required', 'danger')
            return render_template('admin/change_password.html')

        if new_password != confirm_password:
            flash('New passwords do not match', 'danger')
            return render_template('admin/change_password.html')

        try:
            result = user_service.change_password(current_user.user_id, current_password, new_password)
            flash('Password changed successfully!', 'success')
            flash('You can now use your new password on next login.', 'info')

            # Redirect based on role
            role = current_user.role or ''
            if role == 'Admin':
                return redirect(url_for('admin.settings'))
            elif role == 'Supervisor':
                return redirect(url_for('supervisor.dashboard'))
            elif role == 'Prevention Advocate':
                return redirect(url_for('champion.dashboard'))
            else:
                return redirect(url_for('auth.login'))

        except ValueError as e:
            flash(str(e), 'danger')
            return render_template('admin/change_password.html')
        except Exception as e:
            db.session.rollback()
            flash(f'Error changing password: {str(e)}', 'danger')
            return render_template('admin/change_password.html')

    return render_template('admin/change_password.html')


# ============================================
# USER MANAGEMENT ROUTES
# ============================================

@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    """Display all users with their roles and status"""
    users = User.query.order_by(User.username).all()
    return render_template('admin/users.html', users=users, now=datetime.now(timezone.utc))


@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
@limiter.limit("20 per hour", methods=["POST"])
def create_user():
    """Create a new user account"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        role = request.form.get('role', 'supervisor')
        # Normalize role casing to canonical values
        role = (role or '').strip().capitalize()

        # Validation
        if not username:
            flash('Username is required', 'danger')
            return render_template('admin/create_user.html')

        if len(username) < 3:
            flash('Username must be at least 3 characters long', 'danger')
            return render_template('admin/create_user.html')

        # Workstreams preview for dashboard (show key workstreams as cards)
        try:
            from models import MediaGallery, InstitutionalToolkitItem, ResourceItem, BlogPost
            workstreams_preview = [
                {'id': 'podcasts', 'name': 'Podcasts', 'count': Podcast.query.count(), 'route': 'admin.podcasts'},
                {'id': 'seed_funding', 'name': 'Seed Funding', 'count': SeedFundingApplication.query.count(), 'route': 'admin.seed_funding_applications'},
                {'id': 'media_galleries', 'name': 'Media Galleries', 'count': MediaGallery.query.count(), 'route': 'admin.list_media_galleries'},
                {'id': 'institutional_toolkit', 'name': 'Institutional Toolkit', 'count': InstitutionalToolkitItem.query.count(), 'route': 'admin.list_toolkit_items'},
                {'id': 'resources', 'name': 'Resources', 'count': ResourceItem.query.filter_by(published=True).count(), 'route': 'admin.list_resources'},
                {'id': 'stories', 'name': 'Success Stories', 'count': BlogPost.query.filter_by(category='Success Stories').count(), 'route': 'admin.list_stories'}
            ]
        except Exception:
            workstreams_preview = []
        
        # Prevent creating Prevention Advocates through simple user creation
        # They must use create_champion which collects required profile data
        if role == 'Prevention Advocate':
            flash('Prevention Advocates must be created using the "Create Prevention Advocate" form which collects required profile information.', 'warning')
            return redirect(url_for('admin.create_champion'))

        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash(
                f'Username "{username}" already exists. Please choose a different username.', 'danger')
            return render_template('admin/create_user.html')
        
        # Check if email already exists (if provided)
        if email and User.query.filter_by(email=email).first():
            flash(f'Email "{email}" already exists. Please use a different email.', 'danger')
            return render_template('admin/create_user.html')

        try:
            result = user_service.create_user(username, email, role)
            invite_sent = result.get('invite_sent', False)
            return render_template('admin/create_user_success.html',
                                 username=username,
                                 temp_password=None,
                                 role=role,
                                 email=email,
                                 email_sent=invite_sent,
                                 invite_sent=invite_sent)
        except Exception as e:
            current_app.logger.exception('Error creating user')
            flash(f'Error creating user: {str(e)}', 'danger')
            return render_template('admin/create_user.html')

    return render_template('admin/create_user.html')


@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
@limiter.limit("30 per hour", methods=["POST"])
def reset_user_password(user_id):
    """Reset a user's password to a new temporary password"""
    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    try:
        result = user_service.reset_password(user_id)
        temp_password = result.get('temp_password')
        return render_template('admin/create_user_success.html',
                     username=user.username,
                     temp_password=temp_password,
                     role=user.role,
                     email=user.email,
                     email_sent=False,
                     invite_sent=False,
                     is_reset=True)
    except Exception as e:
        current_app.logger.exception('Error resetting user password')
        flash(f'Error resetting password: {str(e)}', 'danger')
        return redirect(url_for('admin.manage_users'))


@admin_bp.route('/users/<int:user_id>/unlock', methods=['POST'])
@login_required
@admin_required
def unlock_user_account(user_id):
    """Unlock a locked user account"""
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    try:
        user_service.unlock_user(user_id)
        flash(f'Account unlocked for user "{user.username}"', 'success')
    except Exception as e:
        current_app.logger.exception('Error unlocking user')
        flash(f'Error unlocking account: {str(e)}', 'danger')

    return redirect(url_for('admin.manage_users'))


@admin_bp.route('/users/<int:user_id>/change-role', methods=['POST'])
@login_required
@admin_required
def change_user_role(user_id):
    """Change a user's role"""
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    new_role_raw = request.form.get('role', '')
    # Try to set role using model helper which handles legacy mappings
    try:
        result = user_service.change_role(user_id, new_role_raw)
        flash(f'Role changed for "{user.username}" from {result.get("old_role")} to {result.get("new_role")}', 'success')
    except ValueError:
        flash('Invalid role selected', 'danger')
    except Exception as e:
        current_app.logger.exception('Error changing role')
        flash(f'Error changing role: {str(e)}', 'danger')

    return redirect(url_for('admin.manage_users'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user account and associated Champion profile"""
    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    # Prevent deleting your own account
    from flask_login import current_user
    if user.user_id == current_user.user_id:
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('admin.manage_users'))

    try:
        user_service.delete_user(user_id, current_user.user_id)
        flash(f'User "{user.username}" and associated records deleted successfully', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    except Exception as e:
        current_app.logger.exception('Error deleting user')
        flash(f'Error deleting user: {str(e)}', 'danger')

    return redirect(url_for('admin.manage_users'))


@admin_bp.route('/champions/create', methods=['GET', 'POST'])
@login_required
@admin_required
@limiter.limit("15 per hour", methods=["POST"])
def create_champion():
    """Create a new champion with user account and profile"""
    if request.method == 'POST':
        # Collect form data and delegate validation/creation to service layer
        username = request.form.get('username', '').strip()
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip() or None
        gender = request.form.get('gender', '').strip() or None
        date_of_birth = request.form.get('date_of_birth', '').strip() or None
        phone_number = request.form.get('phone_number', '').strip()
        county_sub_county = request.form.get('county_sub_county', '').strip() or None
        supervisor_id = request.form.get('supervisor_id', '').strip()

        try:
            sup_id = int(supervisor_id) if supervisor_id else None
            result = champion_service.create_champion(
                username=username,
                full_name=full_name,
                email=email,
                phone_number=phone_number,
                supervisor_id=sup_id,
                gender=gender,
                date_of_birth=date_of_birth,
                county_sub_county=county_sub_county
            )

            invite_sent = result.get('invite_sent', False)
            champion_code = result.get('champion_code')
            supervisor_name = None
            if sup_id:
                try:
                    sup = db.session.get(User, sup_id)
                    if sup:
                        supervisor_name = sup.username
                except Exception:
                    supervisor_name = None

            return render_template('admin/create_user_success.html',
                                 username=username,
                                 temp_password=None,
                                 role=User.ROLE_PREVENTION_ADVOCATE,
                                 email=email,
                                 email_sent=invite_sent,
                                 is_champion=True,
                                 champion_code=champion_code,
                                 full_name=full_name,
                                 supervisor_username=supervisor_name)

        except ValueError as e:
            flash(str(e), 'danger')
            supervisors = User.query.filter_by(role=User.ROLE_SUPERVISOR).all()
            return render_template('admin/create_champion.html', supervisors=supervisors)

        except IntegrityError as e:
            db.session.rollback()
            error_msg = str(e.orig)

            if 'phone_number' in error_msg and 'duplicate' in error_msg.lower():
                flash(f'Phone number "{phone_number}" is already registered. Please use a different phone number.', 'danger')
            elif 'email' in error_msg and 'duplicate' in error_msg.lower():
                flash(f'Email "{email}" is already registered. Please use a different email.', 'danger')
            elif 'username' in error_msg and 'duplicate' in error_msg.lower():
                flash(f'Username "{username}" is already taken. Please choose a different username.', 'danger')
            else:
                flash(f'A champion with this information already exists. Please check phone number, email, and username.', 'danger')

            supervisors = User.query.filter_by(role=User.ROLE_SUPERVISOR).all()
            return render_template('admin/create_champion.html', supervisors=supervisors)

        except Exception as e:
            current_app.logger.exception('Error creating champion')
            flash(f'Error creating champion: {str(e)}', 'danger')
            supervisors = User.query.filter_by(role=User.ROLE_SUPERVISOR).all()
            return render_template('admin/create_champion.html', supervisors=supervisors)

    # GET request - show form with supervisors list
    supervisors = User.query.filter_by(role=User.ROLE_SUPERVISOR).all()
    return render_template('admin/create_champion.html', supervisors=supervisors)


@admin_bp.route('/manage-assignments', methods=['GET'])
@login_required
@admin_required
def manage_assignments():
    """View and manage champion-supervisor assignments"""
    champions = Champion.query.join(User, Champion.user_id == User.user_id).add_columns(
        Champion.champion_id,
        Champion.assigned_champion_code,
        Champion.full_name,
        Champion.supervisor_id,
        Champion.champion_status,
        User.username
    ).all()

    supervisors = User.query.filter_by(role=User.ROLE_SUPERVISOR).all()

    # Group champions by supervisor for easier viewing
    assigned_champions = {}
    unassigned_champions = []

    for champ in champions:
        if champ.supervisor_id:
            if champ.supervisor_id not in assigned_champions:
                assigned_champions[champ.supervisor_id] = []
            assigned_champions[champ.supervisor_id].append(champ)
        else:
            unassigned_champions.append(champ)

    return render_template('admin/manage_assignments.html',
                           champions=champions,
                           supervisors=supervisors,
                           assigned_champions=assigned_champions,
                           unassigned_champions=unassigned_champions)


@admin_bp.route('/assign-champion/<int:champion_id>', methods=['POST'])
@login_required
@admin_required
def assign_champion(champion_id):
    """Assign or reassign a champion to a supervisor"""
    supervisor_id = request.form.get('supervisor_id', '').strip()
    try:
        if supervisor_id:
            res = assignment_service.assign_champion(champion_id, int(supervisor_id))
            old_name = res.get('old_supervisor_name') or 'Unknown'
            new_name = res.get('new_supervisor_name')
            code = res.get('assigned_champion_code') or champion_id
            if old_name == 'Unknown' or old_name is None:
                flash(f'Champion {code} assigned to {new_name}', 'success')
            else:
                flash(f'Champion {code} reassigned from {old_name} to {new_name}', 'success')
        else:
            res = assignment_service.unassign_champion(champion_id)
            old_name = res.get('old_supervisor_name') or 'supervisor'
            code = res.get('assigned_champion_code') or champion_id
            flash(f'Champion {code} unassigned from {old_name}', 'info')
    except ValueError as e:
        flash(str(e), 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating assignment: {str(e)}', 'danger')

    return redirect(url_for('admin.manage_assignments'))


# -----------------------------
# Daily Affirmations CRUD
# -----------------------------
@admin_bp.route('/affirmations')
@login_required
@admin_required
def list_affirmations():
    affirmations = affirmation_service.list_affirmations()
    return render_template('admin/affirmations.html', affirmations=affirmations)


@admin_bp.route('/affirmations/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_affirmation():
    if request.method == 'POST':
        try:
            data = {
                'content': request.form.get('content', '').strip(),
                'theme': request.form.get('theme', '').strip(),
                'scheduled_date': request.form.get('scheduled_date') or None,
            }
            affirmation = affirmation_service.create_affirmation(data, creator_id=current_user.user_id)
            flash('Affirmation created', 'success')
            return redirect(url_for('admin.list_affirmations'))
        except ValueError as e:
            flash(str(e), 'danger')
            return render_template('admin/affirmation_form.html')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating affirmation: {str(e)}', 'danger')
            return render_template('admin/affirmation_form.html')

    return render_template('admin/affirmation_form.html')


@admin_bp.route('/affirmations/<int:affirmation_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_affirmation(affirmation_id):
    affirmation = db.session.get(DailyAffirmation, affirmation_id)
    if not affirmation:
        abort(404)
    if request.method == 'POST':
        try:
            data = {
                'content': request.form.get('content', affirmation.content),
                'theme': request.form.get('theme', affirmation.theme),
                'scheduled_date': request.form.get('scheduled_date') or affirmation.scheduled_date,
            }
            affirmation_service.update_affirmation(affirmation_id, data)
            flash('Affirmation updated', 'success')
            return redirect(url_for('admin.list_affirmations'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating affirmation: {str(e)}', 'danger')
    return render_template('admin/affirmation_form.html', affirmation=affirmation)


@admin_bp.route('/affirmations/<int:affirmation_id>/delete', methods=['POST'])
@login_required
def delete_affirmation(affirmation_id):
    try:
        affirmation_service.delete_affirmation(affirmation_id)
        flash('Affirmation deleted', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting affirmation: {str(e)}', 'danger')
    return redirect(url_for('admin.list_affirmations'))


# -----------------------------
# Symbolic Items CRUD
# -----------------------------
@admin_bp.route('/symbolic-items')
@login_required
def list_symbolic_items():
    items = symbolic_item_service.list_symbolic_items()
    return render_template('admin/symbolic_items.html', items=items)


# -----------------------------
# Media Gallery CRUD
# -----------------------------
@admin_bp.route('/media-galleries')
@login_required
@admin_required
def list_media_galleries():
    galleries = media_gallery_service.list_media_galleries()
    return render_template('admin/media_galleries.html', galleries=galleries)


@admin_bp.route('/media-galleries/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_media_gallery():
    if request.method == 'POST':
        try:
            data = {
                'title': request.form.get('title', '').strip(),
                'description': request.form.get('description'),
                # controller extracts files from request; service will accept saved paths or JSON
                'media_items': request.files.getlist('media_items') or request.form.get('media_items')
            }
            gallery = media_gallery_service.create_media_gallery(data, creator_id=current_user.user_id)
            flash('Media gallery created', 'success')
            return redirect(url_for('admin.list_media_galleries'))
        except ValueError as e:
            flash(str(e), 'danger')
            return render_template('admin/media_gallery_form.html')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating gallery: {str(e)}', 'danger')
            return render_template('admin/media_gallery_form.html')

    return render_template('admin/media_gallery_form.html')


@admin_bp.route('/media-galleries/<int:gallery_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_media_gallery(gallery_id):
    gallery = db.session.get(MediaGallery, gallery_id)
    if not gallery:
        abort(404)
    if request.method == 'POST':
        try:
            data = {
                'title': request.form.get('title', gallery.title),
                'description': request.form.get('description', gallery.description),
                'media_items': request.files.getlist('media_items') or request.form.get('media_items')
            }
            media_gallery_service.update_media_gallery(gallery_id, data)
            flash('Media gallery updated', 'success')
            return redirect(url_for('admin.list_media_galleries'))
        except ValueError as e:
            flash(str(e), 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating gallery: {str(e)}', 'danger')
    return render_template('admin/media_gallery_form.html', gallery=gallery)


@admin_bp.route('/media-galleries/<int:gallery_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_media_gallery(gallery_id):
    try:
        media_gallery_service.delete_media_gallery(gallery_id)
        flash('Media gallery deleted', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting gallery: {str(e)}', 'danger')
    return redirect(url_for('admin.list_media_galleries'))


# -----------------------------
# Institutional Toolkit CRUD
# -----------------------------
@admin_bp.route('/toolkit')
@login_required
@admin_required
def list_toolkit_items():
    items = toolkit_service.list_toolkit_items()
    return render_template('admin/toolkit_items.html', items=items)


@admin_bp.route('/toolkit/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_toolkit_item():
    if request.method == 'POST':
        try:
            data = {
                'title': request.form.get('title', '').strip(),
                'content': request.form.get('content'),
                # prefer files if uploaded
                'attachments': request.files.getlist('attachments') or request.form.get('attachments')
            }
            item = toolkit_service.create_toolkit_item(data, creator_id=current_user.user_id)
            flash('Toolkit item created', 'success')
            return redirect(url_for('admin.list_toolkit_items'))
        except ValueError as e:
            flash(str(e), 'danger')
            return render_template('admin/toolkit_form.html')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating toolkit item: {str(e)}', 'danger')
            return render_template('admin/toolkit_form.html')

    return render_template('admin/toolkit_form.html')


@admin_bp.route('/toolkit/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_toolkit_item(item_id):
    item = db.session.get(InstitutionalToolkitItem, item_id)
    if not item:
        abort(404)
    if request.method == 'POST':
        try:
            data = {
                'title': request.form.get('title', item.title),
                'content': request.form.get('content', item.content),
                'attachments': request.files.getlist('attachments') or request.form.get('attachments')
            }
            toolkit_service.update_toolkit_item(item_id, data)
            flash('Toolkit item updated', 'success')
            return redirect(url_for('admin.list_toolkit_items'))
        except ValueError as e:
            flash(str(e), 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating toolkit item: {str(e)}', 'danger')
    return render_template('admin/toolkit_form.html', item=item)


@admin_bp.route('/toolkit/<int:item_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_toolkit_item(item_id):
    try:
        toolkit_service.delete_toolkit_item(item_id)
        flash('Toolkit item deleted', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting toolkit item: {str(e)}', 'danger')
    return redirect(url_for('admin.list_toolkit_items'))


# -----------------------------
# UMV Global CRUD
# -----------------------------
@admin_bp.route('/umv-global')
@login_required
@admin_required
def list_umv_global():
    entries = umv_service.list_umv_entries()
    return render_template('admin/umv_global.html', entries=entries)


@admin_bp.route('/umv-global/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_umv_entry():
    if request.method == 'POST':
        key = request.form.get('key', '').strip()
        value = request.form.get('value')

        if not key:
            flash('Key is required', 'danger')
            return render_template('admin/umv_form.html')

        try:
            umv_service.create_umv_entry(key, value)
            flash('UMV entry created', 'success')
            return redirect(url_for('admin.list_umv_global'))
        except ValueError as e:
            flash(str(e), 'danger')
            return render_template('admin/umv_form.html')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating UMV entry: {str(e)}', 'danger')
            return render_template('admin/umv_form.html')

    return render_template('admin/umv_form.html')


@admin_bp.route('/umv-global/<int:entry_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_umv_entry(entry_id):
    entry = db.session.get(UMVGlobalEntry, entry_id)
    if not entry:
        abort(404)
    if request.method == 'POST':
        try:
            key = request.form.get('key', entry.key)
            value = request.form.get('value', entry.value)
            umv_service.update_umv_entry(entry_id, key, value)
            flash('UMV entry updated', 'success')
            return redirect(url_for('admin.list_umv_global'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating UMV entry: {str(e)}', 'danger')
    return render_template('admin/umv_form.html', entry=entry)


@admin_bp.route('/umv-global/<int:entry_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_umv_entry(entry_id):
    try:
        umv_service.delete_umv_entry(entry_id)
        flash('UMV entry deleted', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting UMV entry: {str(e)}', 'danger')
    return redirect(url_for('admin.list_umv_global'))


# -----------------------------
# Resources CRUD
# -----------------------------
@admin_bp.route('/resources')
@login_required
@admin_required
def list_resources():
    resources = resource_service.list_resource_items()
    return render_template('admin/resources.html', resources=resources)


@admin_bp.route('/resources/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_resource():
    if request.method == 'POST':
        try:
            data = {
                'title': request.form.get('title', '').strip(),
                'url': request.form.get('url'),
                'description': request.form.get('description'),
                'resource_type': request.form.get('resource_type'),
                'tags': request.form.get('tags')
            }
            resource = resource_service.create_resource_item(data, creator_id=current_user.user_id)
            flash('Resource created', 'success')
            return redirect(url_for('admin.list_resources'))
        except ValueError as e:
            flash(str(e), 'danger')
            return render_template('admin/resource_form.html')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating resource: {str(e)}', 'danger')
            return render_template('admin/resource_form.html')

    return render_template('admin/resource_form.html')


@admin_bp.route('/resources/<int:resource_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_resource(resource_id):
    resource = db.session.get(ResourceItem, resource_id)
    if not resource:
        abort(404)
    if request.method == 'POST':
        try:
            data = {
                'title': request.form.get('title', resource.title),
                'url': request.form.get('url', resource.url),
                'description': request.form.get('description', resource.description),
                'resource_type': request.form.get('resource_type', resource.resource_type),
                'tags': request.form.get('tags')
            }
            resource_service.update_resource_item(resource_id, data)
            flash('Resource updated', 'success')
            return redirect(url_for('admin.list_resources'))
        except ValueError as e:
            flash(str(e), 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating resource: {str(e)}', 'danger')
    return render_template('admin/resource_form.html', resource=resource)


@admin_bp.route('/resources/<int:resource_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_resource(resource_id):
    try:
        resource_service.delete_resource_item(resource_id)
        flash('Resource deleted', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting resource: {str(e)}', 'danger')
    return redirect(url_for('admin.list_resources'))


# -----------------------------
# Stories (use BlogPost with category 'Success Stories')
# -----------------------------
@admin_bp.route('/stories')
@login_required
@admin_required
def list_stories():
    stories = story_service.list_stories()
    return render_template('admin/stories.html', stories=stories)


@admin_bp.route('/stories/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_story():
    if request.method == 'POST':
        try:
            data = {
                'title': request.form.get('title', '').strip(),
                'content': request.form.get('content'),
                'excerpt': request.form.get('excerpt'),
                'featured_image': request.form.get('featured_image')
            }
            story = story_service.create_story(data, author_id=current_user.user_id, publish=True)
            flash('Story created', 'success')
            return redirect(url_for('admin.list_stories'))
        except ValueError as e:
            flash(str(e), 'danger')
            return render_template('admin/story_form.html')
        except IntegrityError:
            db.session.rollback()
            flash('A story with this slug already exists. Please modify the title.', 'danger')
            return render_template('admin/story_form.html')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating story: {str(e)}', 'danger')
            return render_template('admin/story_form.html')

    return render_template('admin/story_form.html')


@admin_bp.route('/stories/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_story(post_id):
    post = db.session.get(BlogPost, post_id)
    if not post:
        abort(404)
    if request.method == 'POST':
        try:
            data = {
                'title': request.form.get('title', post.title),
                'content': request.form.get('content', post.content),
                'excerpt': request.form.get('excerpt', post.excerpt),
                'featured_image': request.form.get('featured_image', post.featured_image)
            }
            story_service.update_story(post_id, data)
            flash('Story updated', 'success')
            return redirect(url_for('admin.list_stories'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating story: {str(e)}', 'danger')
    return render_template('admin/story_form.html', post=post)


@admin_bp.route('/stories/<int:post_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_story(post_id):
    try:
        story_service.delete_story(post_id)
        flash('Story deleted', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting story: {str(e)}', 'danger')
    return redirect(url_for('admin.list_stories'))


@admin_bp.route('/symbolic-items/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_symbolic_item():
    if request.method == 'POST':
        try:
            data = {
                'item_name': request.form.get('item_name', '').strip(),
                'item_type': request.form.get('item_type', '').strip(),
                'description': request.form.get('description', '').strip(),
                'total_quantity': request.form.get('total_quantity')
            }
            symbolic_item_service.create_symbolic_item(data)
            flash('Symbolic item created', 'success')
            return redirect(url_for('admin.list_symbolic_items'))
        except ValueError as e:
            flash(str(e), 'danger')
            return render_template('admin/symbolic_item_form.html')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating item: {str(e)}', 'danger')
    return render_template('admin/symbolic_item_form.html')


@admin_bp.route('/symbolic-items/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_symbolic_item(item_id):
    item = db.session.get(SymbolicItem, item_id)
    if not item:
        abort(404)
    if request.method == 'POST':
        try:
            data = {
                'item_name': request.form.get('item_name', item.item_name),
                'item_type': request.form.get('item_type', item.item_type),
                'description': request.form.get('description', item.description),
                'total_quantity': request.form.get('total_quantity')
            }
            symbolic_item_service.update_symbolic_item(item_id, data)
            flash('Symbolic item updated', 'success')
            return redirect(url_for('admin.list_symbolic_items'))
        except ValueError as e:
            flash(str(e), 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating item: {str(e)}', 'danger')
    return render_template('admin/symbolic_item_form.html', item=item)


@admin_bp.route('/symbolic-items/<int:item_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_symbolic_item(item_id):
    try:
        symbolic_item_service.delete_symbolic_item(item_id)
        flash('Symbolic item deleted', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting item: {str(e)}', 'danger')
    return redirect(url_for('admin.list_symbolic_items'))


# -----------------------------
# Mental Health Assessments CRUD
# -----------------------------
@admin_bp.route('/assessments/manage')
@login_required
@admin_required
def list_assessments_admin():
    assessments = MentalHealthAssessment.query.order_by(MentalHealthAssessment.assessment_date.desc()).all()
    return render_template('admin/assessments.html', assessments=assessments)


@admin_bp.route('/assessments/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_assessment():
    if request.method == 'POST':
        try:
            data = {
                'champion_code': request.form.get('champion_code', '').strip(),
                'assessment_type': request.form.get('assessment_type', '').strip(),
                'risk_category': request.form.get('risk_category', '').strip(),
                'notes': request.form.get('notes', '').strip()
            }
            assessment_service.create_assessment(data, administered_by=current_user.user_id)
            flash('Assessment recorded', 'success')
            return redirect(url_for('admin.list_assessments_admin'))
        except ValueError as e:
            flash(str(e), 'danger')
            return render_template('admin/assessment_form.html')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating assessment: {str(e)}', 'danger')
    return render_template('admin/assessment_form.html')


@admin_bp.route('/assessments/<int:assessment_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_assessment(assessment_id):
    try:
        assessment_service.delete_assessment(assessment_id)
        flash('Assessment deleted', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting assessment: {str(e)}', 'danger')
    return redirect(url_for('admin.list_assessments_admin'))


# ============================================
# HELPER FUNCTIONS
# ============================================

def generate_temp_password(length=12):
    """Generate a secure temporary password"""
    # Mix of uppercase, lowercase, digits, and special characters
    characters = string.ascii_letters + string.digits + '!@#$%&*'

    # Ensure at least one of each type
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice('!@#$%&*')
    ]

    # Fill the rest randomly
    password += [secrets.choice(characters) for _ in range(length - 4)]

    # Shuffle to avoid predictable patterns
    secrets.SystemRandom().shuffle(password)

    return ''.join(password)


@admin_bp.route('/registrations')
@login_required
@admin_required
def registrations():
    """View and manage member registrations"""
    status_filter = request.args.get('status', 'Pending')
    registrations = MemberRegistration.query.filter_by(status=status_filter).order_by(MemberRegistration.submitted_at.desc()).all()
    
    pending_count = MemberRegistration.query.filter_by(status='Pending').count()
    approved_count = MemberRegistration.query.filter_by(status='Approved').count()
    rejected_count = MemberRegistration.query.filter_by(status='Rejected').count()
    
    return render_template('admin/registrations.html',
                         registrations=registrations,
                         status_filter=status_filter,
                         pending_count=pending_count,
                         approved_count=approved_count,
                         rejected_count=rejected_count)


@admin_bp.route('/registrations/<int:registration_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_registration_web(registration_id):
    """Approve a registration from the web interface"""
    try:
        result = registration_service.approve_registration(registration_id, current_user.user_id)
        registration = result.get('registration')
        flash(f'Registration for {registration.full_name} ({registration.username}) has been approved!', 'success')
        return redirect(url_for('admin.registrations'))
    except ValueError as e:
        flash(str(e), 'warning')
        return redirect(url_for('admin.registrations'))
    except Exception as e:
        current_app.logger.exception('Error approving registration')
        flash(f'Error approving registration: {str(e)}', 'danger')
        return redirect(url_for('admin.registrations'))


@admin_bp.route('/registrations/<int:registration_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_registration_web(registration_id):
    """Reject a registration from the web interface"""
    try:
        reason = request.form.get('reason', 'No reason provided')
        registration_service.reject_registration(registration_id, current_user.user_id, reason)
        flash('Registration has been rejected.', 'info')
        return redirect(url_for('admin.registrations'))
    except ValueError as e:
        flash(str(e), 'warning')
        return redirect(url_for('admin.registrations'))
    except Exception as e:
        current_app.logger.exception('Error rejecting registration')
        flash(f'Error rejecting registration: {str(e)}', 'danger')
        return redirect(url_for('admin.registrations'))
        flash(f'Error rejecting registration: {str(e)}', 'danger')
        return redirect(url_for('admin.registrations'))


@admin_bp.route('/champion-applications')
@login_required
@admin_required
def champion_applications():
    """View and manage champion applications"""
    status_filter = request.args.get('status', 'Pending')
    applications = ChampionApplication.query.filter_by(status=status_filter).order_by(ChampionApplication.submitted_at.desc()).all()
    
    pending_count = ChampionApplication.query.filter_by(status='Pending').count()
    approved_count = ChampionApplication.query.filter_by(status='Approved').count()
    rejected_count = ChampionApplication.query.filter_by(status='Rejected').count()
    
    return render_template('admin/champion_applications.html',
                         applications=applications,
                         status_filter=status_filter,
                         pending_count=pending_count,
                         approved_count=approved_count,
                         rejected_count=rejected_count)


@admin_bp.route('/champion-applications/<int:application_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_application_web(application_id):
        """Approve a champion application from the web interface"""
        try:
            result = champion_application_service.approve_application(application_id, current_user.user_id)
            app = result.get('application')
            flash(f'Application for {app.full_name} has been approved.', 'success')
            return redirect(url_for('admin.champion_applications'))
        except ValueError as e:
            flash(str(e), 'warning')
            return redirect(url_for('admin.champion_applications'))
        except Exception as e:
            current_app.logger.exception('Error approving application')
            flash(f'Error approving application: {str(e)}', 'danger')
            return redirect(url_for('admin.champion_applications'))
    


@admin_bp.route('/champion-applications/<int:application_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_application_web(application_id):
    """Reject a champion application from the web interface"""
    try:
        application = db.session.get(ChampionApplication, application_id)
        if not application:
            flash('Application not found', 'warning')
            return redirect(url_for('admin.champion_applications'))
        try:
            reason = request.form.get('reason', 'No reason provided')
            champion_application_service.reject_application(application_id, current_user.user_id, reason)
            flash('Application has been rejected.', 'info')
            return redirect(url_for('admin.champion_applications'))
        except ValueError as e:
            flash(str(e), 'warning')
            return redirect(url_for('admin.champion_applications'))
        except Exception as e:
            current_app.logger.exception('Error rejecting application')
            flash(f'Error rejecting application: {str(e)}', 'danger')
            return redirect(url_for('admin.champion_applications'))
        if application.status != 'Pending':
            flash('Application has already been processed.', 'warning')
            return redirect(url_for('admin.champion_applications'))
        
        reason = request.form.get('reason', 'No reason provided')
        
        application.status = 'Rejected'
        application.reviewed_at = datetime.now(timezone.utc)
        application.reviewed_by = current_user.user_id
        application.rejection_reason = reason
        
        db.session.commit()
        
        flash(f'Champion application for {application.full_name} has been rejected.', 'info')
        return redirect(url_for('admin.champion_applications'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error rejecting application: {str(e)}', 'danger')
        return redirect(url_for('admin.champion_applications'))


@admin_bp.route('/api/pending-counts')
@login_required
@admin_required
def get_pending_counts():
    """API endpoint for getting pending counts (for WebSocket polling)"""
    pending_registrations = MemberRegistration.query.filter_by(status='Pending').count()
    pending_applications = ChampionApplication.query.filter_by(status='Pending').count()
    
    return jsonify({
        'registrations': pending_registrations,
        'applications': pending_applications,
        'total': pending_registrations + pending_applications
    })


# ========================================
# DEBATERS CIRCLE EVENT ROUTES
# ========================================


@admin_bp.route('/debates')
@login_required
@admin_required
def debates():
    """View and manage Debaters Circle events"""
    status_filter = request.args.get('status', 'all')

    query = Event.query.filter(Event.event_type.in_(['debate', 'Debaters Circle']))
    if status_filter != 'all' and status_filter:
        query = query.filter_by(status=status_filter)

    events = query.order_by(Event.event_date.desc()).all()

    total = Event.query.filter(Event.event_type.in_(['debate', 'Debaters Circle'])).count()
    upcoming = Event.query.filter(Event.event_type.in_(['debate', 'Debaters Circle']), Event.status == 'Upcoming').count()
    completed = Event.query.filter(Event.event_type.in_(['debate', 'Debaters Circle']), Event.status == 'Completed').count()

    return render_template(
        'admin/debate_events.html',
        events=events,
        status_filter=status_filter,
        stats={'total': total, 'upcoming': upcoming, 'completed': completed},
        now=datetime.now(timezone.utc)
    )


@admin_bp.route('/debates/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_debate_event():
    """Create a new Debaters Circle event"""
    if request.method == 'POST':
        data = {k: request.form.get(k) for k in ['title', 'motion', 'event_date', 'registration_deadline', 'max_participants', 'description', 'location', 'organizer', 'status', 'image_url']}
        data['event_type'] = 'debate'
        try:
            event_service.create_event(data, current_user.user_id)
            flash('Debaters Circle event created.', 'success')
            return redirect(url_for('admin.debates'))
        except ValueError as e:
            flash(str(e), 'danger')
            return render_template('admin/debate_event_form.html', action='Create', event=None)
        except Exception as e:
            current_app.logger.exception('Error creating event')
            flash(f'Error creating event: {str(e)}', 'danger')
            return render_template('admin/debate_event_form.html', action='Create', event=None)

    return render_template('admin/debate_event_form.html', action='Create', event=None)


@admin_bp.route('/debates/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_debate_event(event_id):
    """Edit an existing Debaters Circle event"""
    event = db.session.get(Event, event_id)
    if not event:
        flash('Event not found', 'warning')
        return redirect(url_for('admin.debates'))
    if event.event_type not in ['debate', 'Debaters Circle']:
        flash('This event is not part of Debaters Circle.', 'warning')
        return redirect(url_for('admin.debates'))

    if request.method == 'POST':
        data = {k: request.form.get(k) for k in ['title', 'motion', 'event_date', 'registration_deadline', 'max_participants', 'description', 'location', 'organizer', 'status', 'image_url']}
        try:
            event_service.update_event(event_id, data)
            flash('Debaters Circle event updated.', 'success')
            return redirect(url_for('admin.debates'))
        except ValueError as e:
            flash(str(e), 'danger')
            return render_template('admin/debate_event_form.html', action='Edit', event=event)
        except Exception as e:
            current_app.logger.exception('Error updating event')
            flash(f'Error updating event: {str(e)}', 'danger')
            return render_template('admin/debate_event_form.html', action='Edit', event=event)

    return render_template('admin/debate_event_form.html', action='Edit', event=event)


@admin_bp.route('/debates/<int:event_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_debate_event(event_id):
    """Delete a Debaters Circle event"""
    event = db.session.get(Event, event_id)
    if not event:
        flash('Event not found', 'warning')
        return redirect(url_for('admin.debates'))
    if event.event_type != 'Debaters Circle':
        flash('This event is not part of Debaters Circle.', 'warning')
        return redirect(url_for('admin.debates'))

    db.session.delete(event)
    db.session.commit()

    flash('Debaters Circle event deleted.', 'success')
    return redirect(url_for('admin.debates'))


# ========================================
# CAMPUS EDITION ROUTES
# ========================================

@admin_bp.route('/campus-edition')
@login_required
@admin_required
def campus_edition():
    """View and manage Campus Edition events"""
    status_filter = request.args.get('status', 'all')

    query = Event.query.filter(Event.event_type == 'campus')
    if status_filter != 'all' and status_filter:
        query = query.filter_by(status=status_filter)

    events = query.order_by(Event.event_date.desc()).all()

    total = Event.query.filter(Event.event_type == 'campus').count()
    upcoming = Event.query.filter(Event.event_type == 'campus', Event.status == 'Upcoming').count()
    completed = Event.query.filter(Event.event_type == 'campus', Event.status == 'Completed').count()

    return render_template(
        'admin/campus_edition.html',
        events=events,
        status_filter=status_filter,
        stats={'total': total, 'upcoming': upcoming, 'completed': completed},
        now=datetime.now(timezone.utc)
    )


@admin_bp.route('/campus-edition/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_campus_event():
    """Create a new Campus Edition event"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        event_date_raw = request.form.get('event_date', '').strip()
        if not title or not event_date_raw:
            flash('Title and event date are required.', 'danger')
            return render_template('admin/campus_event_form.html', action='Create', event=None)

        try:
            event_date = datetime.strptime(event_date_raw, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date format. Please use the provided date picker.', 'danger')
            return render_template('admin/campus_event_form.html', action='Create', event=None)

        registration_deadline = None
        registration_deadline_raw = request.form.get('registration_deadline', '').strip()
        if registration_deadline_raw:
            try:
                registration_deadline = datetime.strptime(registration_deadline_raw, '%Y-%m-%dT%H:%M')
            except ValueError:
                registration_deadline = None

        try:
            max_participants_raw = request.form.get('max_participants')
            max_participants = int(max_participants_raw) if max_participants_raw else None
        except ValueError:
            flash('Max participants must be a number.', 'danger')
            return render_template('admin/campus_event_form.html', action='Create', event=None)

        event = Event(
            title=title,
            description=request.form.get('description'),
            event_date=event_date,
            location=request.form.get('location'),
            event_type='campus',
            organizer=request.form.get('organizer'),
            max_participants=max_participants,
            registration_deadline=registration_deadline,
            status=request.form.get('status', 'Upcoming'),
            image_url=request.form.get('image_url'),
            created_by=current_user.user_id
        )

        db.session.add(event)
        db.session.commit()

        flash('Campus Edition event created.', 'success')
        return redirect(url_for('admin.campus_edition'))

    return render_template('admin/campus_event_form.html', action='Create', event=None)


@admin_bp.route('/campus-edition/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_campus_event(event_id):
    """Edit an existing Campus Edition event"""
    event = db.session.get(Event, event_id)
    if not event:
        flash('Event not found', 'warning')
        return redirect(url_for('admin.campus_edition'))
    if event.event_type != 'campus':
        flash('This event is not part of Campus Edition.', 'warning')
        return redirect(url_for('admin.campus_edition'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        event_date_raw = request.form.get('event_date', '').strip()
        if not title or not event_date_raw:
            flash('Title and event date are required.', 'danger')
            return render_template('admin/campus_event_form.html', action='Edit', event=event)

        try:
            event_date = datetime.strptime(event_date_raw, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date format. Please use the provided date picker.', 'danger')
            return render_template('admin/campus_event_form.html', action='Edit', event=event)

        registration_deadline = None
        registration_deadline_raw = request.form.get('registration_deadline', '').strip()
        if registration_deadline_raw:
            try:
                registration_deadline = datetime.strptime(registration_deadline_raw, '%Y-%m-%dT%H:%M')
            except ValueError:
                registration_deadline = None

        try:
            max_participants_raw = request.form.get('max_participants')
            max_participants = int(max_participants_raw) if max_participants_raw else None
        except ValueError:
            flash('Max participants must be a number.', 'danger')
            return render_template('admin/campus_event_form.html', action='Edit', event=event)

        event.title = title
        event.description = request.form.get('description')
        event.event_date = event_date
        event.location = request.form.get('location')
        event.organizer = request.form.get('organizer')
        event.max_participants = max_participants
        event.registration_deadline = registration_deadline
        event.status = request.form.get('status', 'Upcoming')
        event.image_url = request.form.get('image_url')
        event.updated_at = datetime.now(timezone.utc)

        db.session.commit()

        flash('Campus Edition event updated.', 'success')
        return redirect(url_for('admin.campus_edition'))

    return render_template('admin/campus_event_form.html', action='Edit', event=event)


@admin_bp.route('/campus-edition/<int:event_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_campus_event(event_id):
    """Delete a Campus Edition event"""
    event = db.session.get(Event, event_id)
    if not event:
        flash('Event not found', 'warning')
        return redirect(url_for('admin.campus_edition'))
    if event.event_type != 'campus':
        flash('This event is not part of Campus Edition.', 'warning')
        return redirect(url_for('admin.campus_edition'))

    db.session.delete(event)
    db.session.commit()

    flash('Campus Edition event deleted.', 'success')
    return redirect(url_for('admin.campus_edition'))


# ========================================
# SEED FUNDING ROUTES
# ========================================

@admin_bp.route('/seed-funding')
@login_required
@admin_required
def seed_funding_applications():
    """View and manage seed funding applications"""
    from services.seed_funding_service import list_applications

    status_filter = request.args.get('status', 'all')
    applications, stats = list_applications(status_filter=status_filter)

    return render_template(
        'admin/seed_funding_list.html',
        applications=applications,
        status_filter=status_filter,
        stats=stats,
        now=datetime.now(timezone.utc)
    )


@admin_bp.route('/seed-funding/<int:application_id>')
@login_required
@admin_required
def seed_funding_detail(application_id):
    """View detailed seed funding application"""
    from services.seed_funding_service import get_application

    try:
        application = get_application(application_id)
    except ValueError:
        flash('Application not found', 'warning')
        return redirect(url_for('admin.list_seed_funding'))

    return render_template('admin/seed_funding_detail.html', application=application)


@admin_bp.route('/seed-funding/<int:application_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_seed_funding(application_id):
    """Approve a seed funding application"""
    from services.seed_funding_service import approve_application

    approved_amount = request.form.get('approved_amount')
    approval_conditions = request.form.get('approval_conditions', '').strip()
    admin_notes = request.form.get('admin_notes', '').strip()

    if not approved_amount:
        flash('Approved amount is required.', 'danger')
        return redirect(url_for('admin.seed_funding_detail', application_id=application_id))

    try:
        approve_application(application_id, approved_amount, approval_conditions, admin_notes, current_user.user_id)
        flash(f'Seed funding application approved with KES {float(approved_amount):,.2f}', 'success')
    except ValueError as e:
        flash(str(e), 'warning')
    except Exception as e:
        flash(f'Error approving application: {str(e)}', 'danger')

    return redirect(url_for('admin.seed_funding_detail', application_id=application_id))


@admin_bp.route('/seed-funding/<int:application_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_seed_funding(application_id):
    """Reject a seed funding application"""
    from services.seed_funding_service import reject_application

    rejection_reason = request.form.get('rejection_reason', '').strip()
    admin_notes = request.form.get('admin_notes', '').strip()

    try:
        reject_application(application_id, rejection_reason, admin_notes, current_user.user_id)
        flash('Seed funding application rejected.', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    except Exception as e:
        flash(f'Error rejecting application: {str(e)}', 'danger')

    return redirect(url_for('admin.seed_funding_detail', application_id=application_id))


@admin_bp.route('/seed-funding/<int:application_id>/mark-funded', methods=['POST'])
@login_required
@admin_required
def mark_seed_funding_funded(application_id):
    """Mark a seed funding application as funded (disbursed)"""
    from services.seed_funding_service import mark_as_funded

    disbursement_date_raw = request.form.get('disbursement_date', '').strip()
    disbursement_method = request.form.get('disbursement_method', '').strip()
    disbursement_reference = request.form.get('disbursement_reference', '').strip()

    if not disbursement_date_raw or not disbursement_method:
        flash('Disbursement date and method are required.', 'danger')
        return redirect(url_for('admin.seed_funding_detail', application_id=application_id))

    try:
        mark_as_funded(application_id, disbursement_date_raw, disbursement_method, disbursement_reference)
        flash('Application marked as funded.', 'success')
    except ValueError as e:
        msg = str(e)
        if 'date' in msg.lower():
            flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
        else:
            flash(msg, 'danger')
    except Exception as e:
        flash(f'Error marking as funded: {str(e)}', 'danger')

    return redirect(url_for('admin.seed_funding_detail', application_id=application_id))


@admin_bp.route('/seed-funding/<int:application_id>/update-review-status', methods=['POST'])
@login_required
@admin_required
def update_seed_funding_review_status(application_id):
    """Update seed funding application to Under Review"""
    from services.seed_funding_service import update_review_status

    admin_notes = request.form.get('admin_notes', '').strip()
    try:
        update_review_status(application_id, current_user.user_id, admin_notes or None)
        flash('Application moved to Under Review.', 'success')
    except ValueError:
        flash('Application not found', 'warning')
    except Exception as e:
        flash(f'Error updating review status: {str(e)}', 'danger')

    return redirect(url_for('admin.seed_funding_detail', application_id=application_id))


# ========================================
# UMV MTAANI ROUTES
# ========================================

@admin_bp.route('/umv-mtaani')
@login_required
@admin_required
def umv_mtaani():
    """View and manage UMV Mtaani events"""
    status_filter = request.args.get('status', 'all')

    query = Event.query.filter(Event.event_type == 'mtaani')
    if status_filter != 'all' and status_filter:
        query = query.filter_by(status=status_filter)

    events = query.order_by(Event.event_date.desc()).all()

    total = Event.query.filter(Event.event_type == 'mtaani').count()
    upcoming = Event.query.filter(Event.event_type == 'mtaani', Event.status == 'Upcoming').count()
    completed = Event.query.filter(Event.event_type == 'mtaani', Event.status == 'Completed').count()

    return render_template(
        'admin/umv_mtaani.html',
        events=events,
        status_filter=status_filter,
        stats={'total': total, 'upcoming': upcoming, 'completed': completed},
        now=datetime.now(timezone.utc)
    )


@admin_bp.route('/umv-mtaani/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_mtaani_event():
    """Create a new UMV Mtaani event"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        event_date_raw = request.form.get('event_date', '').strip()
        if not title or not event_date_raw:
            flash('Title and event date are required.', 'danger')
            return render_template('admin/mtaani_event_form.html', action='Create', event=None)

        try:
            event_date = datetime.strptime(event_date_raw, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date format. Please use the provided date picker.', 'danger')
            return render_template('admin/mtaani_event_form.html', action='Create', event=None)

        registration_deadline = None
        registration_deadline_raw = request.form.get('registration_deadline', '').strip()
        if registration_deadline_raw:
            try:
                registration_deadline = datetime.strptime(registration_deadline_raw, '%Y-%m-%dT%H:%M')
            except ValueError:
                registration_deadline = None

        try:
            max_participants_raw = request.form.get('max_participants')
            max_participants = int(max_participants_raw) if max_participants_raw else None
        except ValueError:
            flash('Max participants must be a number.', 'danger')
            return render_template('admin/mtaani_event_form.html', action='Create', event=None)

        event = Event(
            title=title,
            description=request.form.get('description'),
            event_date=event_date,
            location=request.form.get('location'),
            event_type='mtaani',
            organizer=request.form.get('organizer'),
            max_participants=max_participants,
            registration_deadline=registration_deadline,
            status=request.form.get('status', 'Upcoming'),
            image_url=request.form.get('image_url'),
            created_by=current_user.user_id
        )

        db.session.add(event)
        db.session.commit()

        flash('UMV Mtaani event created.', 'success')
        return redirect(url_for('admin.umv_mtaani'))

    return render_template('admin/mtaani_event_form.html', action='Create', event=None)


@admin_bp.route('/umv-mtaani/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_mtaani_event(event_id):
    """Edit an existing UMV Mtaani event"""
    event = db.session.get(Event, event_id)
    if not event:
        flash('Event not found', 'warning')
        return redirect(url_for('admin.umv_mtaani'))
    if event.event_type != 'mtaani':
        flash('This event is not part of UMV Mtaani.', 'warning')
        return redirect(url_for('admin.umv_mtaani'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        event_date_raw = request.form.get('event_date', '').strip()
        if not title or not event_date_raw:
            flash('Title and event date are required.', 'danger')
            return render_template('admin/mtaani_event_form.html', action='Edit', event=event)

        try:
            event_date = datetime.strptime(event_date_raw, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date format. Please use the provided date picker.', 'danger')
            return render_template('admin/mtaani_event_form.html', action='Edit', event=event)

        registration_deadline = None
        registration_deadline_raw = request.form.get('registration_deadline', '').strip()
        if registration_deadline_raw:
            try:
                registration_deadline = datetime.strptime(registration_deadline_raw, '%Y-%m-%dT%H:%M')
            except ValueError:
                registration_deadline = None

        try:
            max_participants_raw = request.form.get('max_participants')
            max_participants = int(max_participants_raw) if max_participants_raw else None
        except ValueError:
            flash('Max participants must be a number.', 'danger')
            return render_template('admin/mtaani_event_form.html', action='Edit', event=event)

        event.title = title
        event.description = request.form.get('description')
        event.event_date = event_date
        event.location = request.form.get('location')
        event.organizer = request.form.get('organizer')
        event.max_participants = max_participants
        event.registration_deadline = registration_deadline
        event.status = request.form.get('status', 'Upcoming')
        event.image_url = request.form.get('image_url')
        event.updated_at = datetime.now(timezone.utc)

        db.session.commit()

        flash('UMV Mtaani event updated.', 'success')
        return redirect(url_for('admin.umv_mtaani'))

    return render_template('admin/mtaani_event_form.html', action='Edit', event=event)


@admin_bp.route('/umv-mtaani/<int:event_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_mtaani_event(event_id):
    """Delete a UMV Mtaani event"""
    event = db.session.get(Event, event_id)
    if not event:
        flash('Event not found', 'warning')
        return redirect(url_for('admin.umv_mtaani'))
    if event.event_type != 'mtaani':
        flash('This event is not part of UMV Mtaani.', 'warning')
        return redirect(url_for('admin.umv_mtaani'))

    db.session.delete(event)
    db.session.commit()

    flash('UMV Mtaani event deleted.', 'success')
    return redirect(url_for('admin.umv_mtaani'))


# ========================================
# PODCAST MANAGEMENT ROUTES
# ========================================

@admin_bp.route('/podcasts')
@login_required
@admin_required
def podcasts():
    """View and manage podcasts"""
    status_filter = request.args.get('status', 'all')
    category_filter = request.args.get('category', 'all')
    
    query = Podcast.query
    
    # Filter by status
    if status_filter == 'published':
        query = query.filter_by(published=True)
    elif status_filter == 'draft':
        query = query.filter_by(published=False)
    
    # Filter by category
    if category_filter != 'all':
        query = query.filter_by(category=category_filter)
    
    # Order by created date descending
    podcasts = query.order_by(Podcast.created_at.desc()).all()
    
    # Get all unique categories
    categories = db.session.query(Podcast.category)\
        .filter(Podcast.category.isnot(None))\
        .distinct()\
        .all()
    category_list = [cat[0] for cat in categories]
    
    # Get counts
    total_count = Podcast.query.count()
    published_count = Podcast.query.filter_by(published=True).count()
    draft_count = Podcast.query.filter_by(published=False).count()
    
    return render_template('admin/podcasts.html',
                         podcasts=podcasts,
                         status_filter=status_filter,
                         category_filter=category_filter,
                         categories=category_list,
                         total_count=total_count,
                         published_count=published_count,
                         draft_count=draft_count)


@admin_bp.route('/podcasts/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_podcast():
    """Create a new podcast"""
    if request.method == 'POST':
        try:
            data = {
                'title': request.form.get('title'),
                'description': request.form.get('description'),
                'guest': request.form.get('guest'),
                'audio_url': request.form.get('audio_url'),
                'thumbnail_url': request.form.get('thumbnail_url'),
                'duration': request.form.get('duration'),
                'episode_number': request.form.get('episode_number'),
                'season_number': request.form.get('season_number'),
                'category': request.form.get('category'),
                'tags': request.form.get('tags', ''),
                'published': request.form.get('published') == 'on'
            }
            podcast_service.create_podcast(data, creator_id=current_user.user_id)
            flash('Podcast created successfully!', 'success')
            return redirect(url_for('admin.podcasts'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating podcast: {str(e)}', 'error')
    
    return render_template('admin/podcast_form.html', podcast=None, action='Create')


@admin_bp.route('/podcasts/<int:podcast_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_podcast(podcast_id):
    """Edit an existing podcast"""
    podcast = db.session.get(Podcast, podcast_id)
    if not podcast:
        flash('Podcast not found', 'warning')
        return redirect(url_for('admin.podcasts'))

    if request.method == 'POST':
        try:
            data = {
                'title': request.form.get('title'),
                'description': request.form.get('description'),
                'guest': request.form.get('guest'),
                'audio_url': request.form.get('audio_url'),
                'thumbnail_url': request.form.get('thumbnail_url'),
                'duration': request.form.get('duration'),
                'episode_number': request.form.get('episode_number'),
                'season_number': request.form.get('season_number'),
                'category': request.form.get('category'),
                'tags': request.form.get('tags', ''),
                'published': request.form.get('published') == 'on'
            }
            podcast_service.update_podcast(podcast_id, data)
            flash('Podcast updated successfully!', 'success')
            return redirect(url_for('admin.podcasts'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating podcast: {str(e)}', 'error')

    return render_template('admin/podcast_form.html', podcast=podcast, action='Edit')


@admin_bp.route('/podcasts/<int:podcast_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_podcast(podcast_id):
    """Delete a podcast"""
    try:
        podcast_service.delete_podcast(podcast_id)
        flash('Podcast deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting podcast: {str(e)}', 'error')
    
    return redirect(url_for('admin.podcasts'))


@admin_bp.route('/podcasts/<int:podcast_id>/toggle-publish', methods=['POST'])
@login_required
@admin_required
def toggle_publish_podcast(podcast_id):
    """Toggle podcast published status"""
    try:
        podcast_service.toggle_publish_podcast(podcast_id)
        refreshed = db.session.get(Podcast, podcast_id)
        if not refreshed:
            flash('Podcast not found', 'warning')
            return redirect(url_for('admin.podcasts'))
        status = 'published' if refreshed.published else 'unpublished'
        flash(f'Podcast {status} successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating podcast: {str(e)}', 'error')
    
    return redirect(url_for('admin.podcasts'))


# ========================================
# WORKSTREAMS MANAGEMENT (Unified CRUD Interface)
# ========================================

@admin_bp.route('/workstreams')
@login_required
@admin_required
def workstreams():
    """Unified workstreams management dashboard"""
    from models import SeedFundingApplication
    
    from models import MediaGallery, InstitutionalToolkitItem, ResourceItem, BlogPost

    workstreams_data = [
        {
            'id': 'podcasts',
            'name': 'Podcasts',
            'description': 'Manage podcast episodes and guests',
            'icon': 'podcast',
            'route': 'admin.podcasts',
            'create_route': 'admin.create_podcast',
            'count': Podcast.query.count()
        },
        {
            'id': 'debators_circle',
            'name': 'Debators Circle',
            'description': 'Manage debate events and champion participation',
            'icon': 'mic',
            'route': 'admin.debates',
            'create_route': 'admin.create_debate_event',
            'count': Event.query.filter(Event.event_type.in_(['debate', 'Debaters Circle'])).count()
        },
        {
            'id': 'campus_edition',
            'name': 'Campus Edition',
            'description': 'Manage campus-based events and activities',
            'icon': 'training',
            'route': 'admin.campus_edition',
            'create_route': 'admin.create_campus_event',
            'count': Event.query.filter(Event.event_type == 'campus').count()
        },
        {
            'id': 'seed_funding',
            'name': 'Seed Funding',
            'description': 'Review and approve seed funding applications',
            'icon': 'funding',
            'route': 'admin.seed_funding_applications',
            'create_route': None,  # Applications come from frontend
            'count': SeedFundingApplication.query.count()
        },
        {
            'id': 'umv_mtaani',
            'name': 'UMV Mtaani',
            'description': 'Manage community barazas and mtaani events',
            'icon': 'community',
            'route': 'admin.umv_mtaani',
            'create_route': 'admin.create_mtaani_event',
            'count': Event.query.filter(Event.event_type == 'mtaani').count()
        }
    ]

    # Add content-focused workstreams (media, toolkit, resources, stories)
    try:
        workstreams_data.extend([
            {
                'id': 'media_galleries',
                'name': 'Media Galleries',
                'description': 'Manage image and video galleries used across the site',
                'icon': 'gallery',
                'route': 'admin.list_media_galleries',
                'create_route': 'admin.create_media_gallery',
                'count': MediaGallery.query.count()
            },
            {
                'id': 'institutional_toolkit',
                'name': 'Institutional Toolkit',
                'description': 'Guides, templates and checklists for institutions',
                'icon': 'toolkit',
                'route': 'admin.list_toolkit_items',
                'create_route': 'admin.create_toolkit_item',
                'count': InstitutionalToolkitItem.query.count()
            },
            {
                'id': 'resources',
                'name': 'Resources',
                'description': 'External/internal resource links and documents',
                'icon': 'link',
                'route': 'admin.list_resources',
                'create_route': 'admin.create_resource',
                'count': ResourceItem.query.count()
            },
            {
                'id': 'stories',
                'name': 'Success Stories',
                'description': 'Manage success stories / case studies',
                'icon': 'star',
                'route': 'admin.list_stories',
                'create_route': 'admin.create_story',
                'count': BlogPost.query.filter_by(category='Success Stories').count()
            }
        ])
    except Exception:
        # If models/tables not present yet (migration state), fallback to zero counts
        workstreams_data.extend([
            {'id': 'media_galleries','name':'Media Galleries','description':'Manage image and video galleries used across the site','icon':'gallery','route':'admin.list_media_galleries','create_route':'admin.create_media_gallery','count':0},
            {'id': 'institutional_toolkit','name':'Institutional Toolkit','description':'Guides, templates and checklists for institutions','icon':'toolkit','route':'admin.list_toolkit_items','create_route':'admin.create_toolkit_item','count':0},
            {'id': 'resources','name':'Resources','description':'External/internal resource links and documents','icon':'link','route':'admin.list_resources','create_route':'admin.create_resource','count':0},
            {'id': 'stories','name':'Success Stories','description':'Manage success stories / case studies','icon':'star','route':'admin.list_stories','create_route':'admin.create_story','count':0}
        ])
    # Additional workstreams: affirmations, symbolic items, assessments
    try:
        workstreams_data.extend([
            {
                'id': 'affirmations',
                'name': 'Affirmations',
                'description': 'Manage daily affirmations and schedules',
                'icon': 'chat',
                'route': 'admin.affirmations',
                'create_route': 'admin.affirmation_form',
                'count': DailyAffirmation.query.count()
            },
            {
                'id': 'symbolic_items',
                'name': 'Symbolic Items',
                'description': 'Items and symbolic resources used in sessions',
                'icon': 'item',
                'route': 'admin.list_symbolic_items',
                'create_route': 'admin.symbolic_item_form',
                'count': SymbolicItem.query.count()
            }
        ])
    except Exception:
        workstreams_data.extend([
            {'id': 'affirmations','name':'Affirmations','description':'Manage daily affirmations and schedules','icon':'chat','route':'admin.affirmations','create_route':'admin.affirmation_form','count':0},
            {'id': 'symbolic_items','name':'Symbolic Items','description':'Items and symbolic resources used in sessions','icon':'item','route':'admin.list_symbolic_items','create_route':'admin.symbolic_item_form','count':0}
        ])
    
    return render_template('admin/workstreams.html', workstreams=workstreams_data)


# ========================================
# AFFIRMATIONS MANAGEMENT
# ========================================

@admin_bp.route('/affirmations')
@login_required
@admin_required
def affirmations():
    """List all daily affirmations"""
    theme_filter = request.args.get('theme', '')
    active_only = request.args.get('active', 'true').lower() == 'true'
    
    query = DailyAffirmation.query
    
    if theme_filter:
        query = query.filter_by(theme=theme_filter)
    if active_only:
        query = query.filter_by(active=True)
    
    affirmations = query.order_by(DailyAffirmation.scheduled_date.desc()).all()
    themes = db.session.query(DailyAffirmation.theme).distinct().filter(DailyAffirmation.theme.isnot(None)).all()
    
    return render_template('admin/affirmations_list.html',
                         affirmations=affirmations,
                         themes=[t[0] for t in themes],
                         theme_filter=theme_filter,
                         active_only=active_only)


@admin_bp.route('/affirmations/create', methods=['GET', 'POST'])
@login_required
@admin_required
def affirmation_form():
    """Create a new affirmation"""
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        theme = request.form.get('theme', 'General').strip()
        scheduled_date = request.form.get('scheduled_date', '').strip()
        
        if not content:
            flash('Content is required', 'danger')
            return render_template('admin/affirmation_form.html')
        
        try:
            affirmation = DailyAffirmation(
                content=content,
                theme=theme,
                scheduled_date=datetime.strptime(scheduled_date, '%Y-%m-%d').date() if scheduled_date else None,
                active=True,
                created_by=current_user.user_id
            )
            
            db.session.add(affirmation)
            db.session.commit()
            
            flash(f'Affirmation created successfully!', 'success')
            return redirect(url_for('admin.affirmations'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating affirmation: {str(e)}', 'danger')
            return render_template('admin/affirmation_form.html')
    
    return render_template('admin/affirmation_form.html')


@admin_bp.route('/affirmations/<int:affirmation_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def affirmation_edit(affirmation_id):
    """Edit an affirmation"""
    affirmation = db.session.get(DailyAffirmation, affirmation_id)
    if not affirmation:
        flash('Affirmation not found', 'warning')
        return redirect(url_for('admin.affirmations'))
    
    if request.method == 'POST':
        affirmation.content = request.form.get('content', '').strip()
        affirmation.theme = request.form.get('theme', 'General').strip()
        scheduled_date = request.form.get('scheduled_date', '').strip()
        affirmation.active = request.form.get('active') == 'on'
        affirmation.updated_at = datetime.now(timezone.utc)
        
        if scheduled_date:
            try:
                affirmation.scheduled_date = datetime.strptime(scheduled_date, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format', 'danger')
                return render_template('admin/affirmation_form.html', affirmation=affirmation, action='Edit')
        
        try:
            db.session.commit()
            flash('Affirmation updated successfully!', 'success')
            return redirect(url_for('admin.affirmations'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating affirmation: {str(e)}', 'danger')
    
    return render_template('admin/affirmation_form.html', affirmation=affirmation, action='Edit')


@admin_bp.route('/affirmations/<int:affirmation_id>/delete', methods=['POST'])
@login_required
@admin_required
def affirmation_delete(affirmation_id):
    """Delete (deactivate) an affirmation"""
    try:
        affirmation = db.session.get(DailyAffirmation, affirmation_id)
        if not affirmation:
            flash('Affirmation not found', 'warning')
            return redirect(url_for('admin.affirmations'))
        affirmation.active = False
        db.session.commit()
        
        flash('Affirmation deactivated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting affirmation: {str(e)}', 'danger')
    
    return redirect(url_for('admin.affirmations'))


# ========================================
# SYMBOLIC ITEMS MANAGEMENT
# ========================================

@admin_bp.route('/symbolic-items')
@login_required
@admin_required
def symbolic_items():
    """List all symbolic items"""
    item_type_filter = request.args.get('type', '')
    
    query = SymbolicItem.query
    
    if item_type_filter:
        query = query.filter_by(item_type=item_type_filter)
    
    items = query.order_by(SymbolicItem.item_id.desc()).all()
    item_types = db.session.query(SymbolicItem.item_type).distinct().filter(SymbolicItem.item_type.isnot(None)).all()
    
    return render_template('admin/symbolic_items_list.html',
                         items=items,
                         item_types=[t[0] for t in item_types],
                         item_type_filter=item_type_filter)


@admin_bp.route('/symbolic-items/create', methods=['GET', 'POST'])
@login_required
@admin_required
def symbolic_item_form():
    """Create a new symbolic item"""
    if request.method == 'POST':
        item_name = request.form.get('item_name', '').strip()
        item_type = request.form.get('item_type', '').strip()
        total_quantity = request.form.get('total_quantity', '0').strip()
        
        if not item_name or not item_type:
            flash('Item name and type are required', 'danger')
            return render_template('admin/symbolic_item_form.html')
        
        try:
            total_qty = int(total_quantity) if total_quantity else 0
            
            item = SymbolicItem(
                item_name=item_name,
                item_type=item_type,
                description=request.form.get('description', '').strip() or None,
                linked_to_training_module=request.form.get('linked_to_training_module', '').strip() or None,
                total_quantity=total_qty
            )
            
            db.session.add(item)
            db.session.commit()
            
            flash(f'Symbolic item "{item_name}" created successfully!', 'success')
            return redirect(url_for('admin.symbolic_items'))
            
        except ValueError:
            flash('Quantity must be a number', 'danger')
            return render_template('admin/symbolic_item_form.html')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating item: {str(e)}', 'danger')
            return render_template('admin/symbolic_item_form.html')
    
    return render_template('admin/symbolic_item_form.html')


@admin_bp.route('/symbolic-items/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def symbolic_item_edit(item_id):
    """Edit a symbolic item"""
    item = db.session.get(SymbolicItem, item_id)
    if not item:
        flash('Item not found', 'warning')
        return redirect(url_for('admin.symbolic_items'))
    
    if request.method == 'POST':
        item.item_name = request.form.get('item_name', '').strip()
        item.item_type = request.form.get('item_type', '').strip()
        item.description = request.form.get('description', '').strip() or None
        item.linked_to_training_module = request.form.get('linked_to_training_module', '').strip() or None
        
        try:
            total_qty = int(request.form.get('total_quantity', '0').strip())
            item.total_quantity = total_qty
            
            db.session.commit()
            flash('Symbolic item updated successfully!', 'success')
            return redirect(url_for('admin.symbolic_items'))
        except ValueError:
            flash('Quantity must be a number', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating item: {str(e)}', 'danger')
    
    return render_template('admin/symbolic_item_form.html', item=item, action='Edit')


@admin_bp.route('/symbolic-items/<int:item_id>/delete', methods=['POST'])
@login_required
@admin_required
def symbolic_item_delete(item_id):
    """Delete a symbolic item"""
    try:
        item = db.session.get(SymbolicItem, item_id)
        if not item:
            flash('Item not found', 'warning')
            return redirect(url_for('admin.symbolic_items'))
        db.session.delete(item)
        db.session.commit()
        
        flash('Symbolic item deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting item: {str(e)}', 'danger')
    
    return redirect(url_for('admin.symbolic_items'))


# ========================================
# ASSESSMENTS MANAGEMENT (View Only)
# ========================================

@admin_bp.route('/assessments')
@login_required
@admin_required
def assessments():
    """
    List all mental health assessments - PRIVACY-FIRST VIEW
    Shows aggregated data with risk categories, NOT raw scores or champion names
    """
    assessment_type = request.args.get('type', '')
    risk_category = request.args.get('risk_category', '')
    
    query = MentalHealthAssessment.query
    
    if assessment_type:
        query = query.filter_by(assessment_type=assessment_type)
    if risk_category:
        query = query.filter_by(risk_category=risk_category)
    
    assessments = query.order_by(MentalHealthAssessment.assessment_date.desc()).all()
    assessment_types = db.session.query(MentalHealthAssessment.assessment_type).distinct().all()
    risk_categories = db.session.query(MentalHealthAssessment.risk_category).distinct().all()
    
    return render_template('admin/assessments_list.html',
                         assessments=assessments,
                         assessment_types=[t[0] for t in assessment_types if t[0]],
                         risk_categories=[r[0] for r in risk_categories if r[0]],
                         assessment_type=assessment_type,
                         risk_category=risk_category)


@admin_bp.route('/assessments/<int:assessment_id>')
@login_required
@admin_required
def assessment_detail(assessment_id):
    """
    View assessment details - PRIVACY: Shows risk category, NOT raw scores
    Champion code is displayed but NOT the champion name
    """
    assessment = db.session.get(MentalHealthAssessment, assessment_id)
    if not assessment:
        flash('Assessment not found', 'warning')
        return redirect(url_for('admin.assessments'))

    return render_template('admin/assessment_detail.html', assessment=assessment)


@admin_bp.route('/test-email', methods=['GET', 'POST'])
@login_required
@admin_required
def test_email():
    """Test email configuration - admin diagnostic tool"""
    if request.method == 'POST':
        test_recipient = request.form.get('test_email', '').strip()
        
        if not test_recipient:
            flash('Please enter an email address', 'danger')
            return redirect(url_for('admin.test_email'))
        # Respect global disable flag: do not send test emails when emailing is disabled
        if current_app.config.get('DISABLE_EMAILS') or current_app.config.get('DISABLE_EMAIL_IN_BUILD'):
            current_app.logger.info(f"Email testing skipped because emailing is disabled; attempted to test {test_recipient}")
            flash('Email sending is currently disabled by configuration. No test email was sent.', 'warning')
            return redirect(url_for('admin.test_email'))

        try:
            current_app.logger.info(f"Admin {current_user.username} testing email to {test_recipient}")
            email_sent = send_password_email(
                recipient_email=test_recipient,
                username="test_user",
                temp_password="TestPass123!"
            )
            
            if email_sent:
                flash(f'Test email sent successfully to {test_recipient}. Check inbox and spam folder.', 'success')
            else:
                flash(f'Email sending failed. Check server logs for details.', 'danger')
                
        except Exception as e:
            current_app.logger.error(f"Email test error: {str(e)}")
            flash(f'Email error: {str(e)}', 'danger')
        
        return redirect(url_for('admin.test_email'))
    
    # GET request - show email config
    config_status = {
        'MAIL_SERVER': current_app.config.get('MAIL_SERVER'),
        'MAIL_PORT': current_app.config.get('MAIL_PORT'),
        'MAIL_USE_TLS': current_app.config.get('MAIL_USE_TLS'),
        'MAIL_USERNAME': current_app.config.get('MAIL_USERNAME'),
        'MAIL_PASSWORD': 'Set' if current_app.config.get('MAIL_PASSWORD') else 'Missing',
        'MAIL_DEFAULT_SENDER': current_app.config.get('MAIL_DEFAULT_SENDER'),
    }
    
    return render_template('admin/test_email.html', config=config_status)
