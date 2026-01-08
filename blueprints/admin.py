from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
import threading
from flask_login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from models import db, Champion, YouthSupport, RefferalPathway, TrainingRecord, get_champions_needing_refresher, get_high_risk_champions, get_overdue_reviews, User, MemberRegistration, ChampionApplication, Podcast, Event, DailyAffirmation, SymbolicItem, MentalHealthAssessment
from decorators import admin_required
from flask_bcrypt import Bcrypt
import secrets
import string
from datetime import datetime
from email_utils import send_password_email
from extensions import limiter
from extensions import limiter

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # HIGH-LEVEL DASHBOARD METRICS

    # CHAMPION STATUS TRACKING
    total_champions = Champion.query.count()
    active_champions = Champion.query.filter_by(
        champion_status='Active').count()
    inactive_champions = Champion.query.filter_by(
        champion_status='Inactive').count()
    on_hold_champions = Champion.query.filter_by(
        champion_status='On Hold').count()

    # 1. Average Check-In Completion Rate
    # This calculates the rounded average of all weekly check-in completion rates
    average_check_in = db.session.query(
        func.avg(YouthSupport.weekly_check_in_completion_rate)).scalar() or 0
    # Rounded to nearest percentage
    avg_check_in_rounded = round(average_check_in, 0)

    # 1b. Average Mini-Screening Completion Rate
    # Calculate percentage of mini-screenings completed vs expected
    total_expected_screenings = db.session.query(
        func.count(YouthSupport.support_id)).scalar() or 0
    total_completed_screenings = db.session.query(
        func.sum(YouthSupport.monthly_mini_screenings_delivered)).scalar() or 0
    avg_screening_completion_rate = (
        total_completed_screenings / total_expected_screenings) if total_expected_screenings > 0 else 0

    # 2. Referral Conversion Rate (Success Rate)
    # Ratio of "Attended" outcomes vs total referrals
    total_referrals = RefferalPathway.query.count()
    successful_referrals = RefferalPathway.query.filter_by(
        referal_outcomes='Attended').count()
    conversion_rate = (successful_referrals /
                       total_referrals * 100) if total_referrals > 0 else 0

    # 3. Training Compliance Rate
    # Percentage of champions with "Certified" status for core modules
    total_training_records = TrainingRecord.query.count()
    certified_records = TrainingRecord.query.filter_by(
        certification_status='Certified').count()
    training_compliance_rate = (
        certified_records / total_training_records * 100) if total_training_records > 0 else 0

    # Core modules compliance check
    core_modules = ['Safeguarding', 'Referral Protocols']
    champions_with_core_training = (
        db.session.query(Champion.champion_id)
        .join(TrainingRecord)
        .filter(TrainingRecord.training_module.in_(core_modules))
        .filter(TrainingRecord.certification_status == 'Certified')
        .distinct()
        .count()
    )

    # 4. Total Youth Reached per Champion
    # Aggregates youth from support records and referrals
    youth_per_champion = (
        db.session.query(
            Champion.champion_id,
            Champion.full_name,
            Champion.assigned_champion_code,
            func.coalesce(func.max(YouthSupport.number_of_youth_under_support), 0).label(
                'total_youth')
        )
        .outerjoin(YouthSupport)
        .group_by(Champion.champion_id, Champion.full_name, Champion.assigned_champion_code)
        .all()
    )

    # Total youth reached across all champions
    total_youth_reached = db.session.query(
        func.sum(YouthSupport.number_of_youth_under_support)).scalar() or 0

    # 5. Quarterly Satisfaction Score
    # Average of youth feedback scores (self_reported_wellbeing_check)
    quarterly_satisfaction = db.session.query(
        func.avg(YouthSupport.self_reported_wellbeing_check)).scalar() or 0
    quarterly_satisfaction_rounded = round(quarterly_satisfaction, 1)

    # 6. Recruitment Source Analytics (Operational Clarity)
    recruitment_sources = (
        db.session.query(
            Champion.recruitment_source,
            func.count(Champion.champion_id).label('count')
        )
        .filter(Champion.recruitment_source.isnot(None))
        .group_by(Champion.recruitment_source)
        .all()
    )

    # 7. Clinical Reliability - Average Flag-to-Referral Time
    avg_flag_to_referral = db.session.query(
        func.avg(RefferalPathway.flag_to_referral_days)).scalar() or 0
    avg_flag_to_referral_rounded = round(avg_flag_to_referral, 1)

    # CONSENT & LEGAL COMPLIANCE CHECK
    champions_missing_consent = Champion.query.filter_by(
        consent_obtained=False).count()
    champions_missing_institution = Champion.query.filter_by(
        institution_consent_obtained=False).count()

    # REFRESHER ALERTS (next 30 days)
    upcoming_refreshers = get_champions_needing_refresher(days_ahead=30)
    
    # PENDING REGISTRATIONS & APPLICATIONS
    pending_registrations_count = MemberRegistration.query.filter_by(status='Pending').count()
    pending_applications_count = ChampionApplication.query.filter_by(status='Pending').count()

    return render_template('admin/dashboard.html',
                           # Champion Status Counts
                           total_champions=total_champions,
                           active_champions=active_champions,
                           inactive_champions=inactive_champions,
                           on_hold_champions=on_hold_champions,

                           # Performance Metrics
                           avg_check_in=avg_check_in_rounded,
                           avg_screening_completion_rate=round(
                               avg_screening_completion_rate, 1),
                           conversion_rate=round(conversion_rate, 1),
                           training_compliance_rate=round(
                               training_compliance_rate, 1),
                           champions_with_core_training=champions_with_core_training,

                           # Youth Reach
                           youth_per_champion=youth_per_champion,
                           total_youth_reached=total_youth_reached,

                           # Satisfaction & Quality
                           quarterly_satisfaction=quarterly_satisfaction_rounded,

                           # Operational Analytics
                           recruitment_sources=recruitment_sources,
                           avg_flag_to_referral=avg_flag_to_referral_rounded,

                           # Compliance
                           champions_missing_consent=champions_missing_consent,
                           champions_missing_institution=champions_missing_institution,
                           upcoming_refreshers=upcoming_refreshers,

                           # SAFETY ALERTS
                           high_risk_champions=get_high_risk_champions(),
                           overdue_reviews=get_overdue_reviews(),
                           high_risk_count=len(get_high_risk_champions()),
                           overdue_count=len(get_overdue_reviews()),
                           
                           # PENDING APPROVALS
                           pending_registrations_count=pending_registrations_count,
                           pending_applications_count=pending_applications_count
                           )


@admin_bp.route('/settings')
@login_required
@admin_required
def settings():
    """User profile and account settings"""
    return render_template('admin/settings.html', user=current_user)


@admin_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Allow any user to change their own password"""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validation
        if not current_password or not new_password or not confirm_password:
            flash('All fields are required', 'danger')
            return render_template('admin/change_password.html')

        # Verify current password
        bcrypt = Bcrypt()
        if not bcrypt.check_password_hash(current_user.password_hash, current_password):
            flash('Current password is incorrect', 'danger')
            return render_template('admin/change_password.html')

        # Check new password matches confirmation
        if new_password != confirm_password:
            flash('New passwords do not match', 'danger')
            return render_template('admin/change_password.html')

        # Validate new password strength
        if len(new_password) < 8:
            flash('New password must be at least 8 characters long', 'danger')
            return render_template('admin/change_password.html')

        # Check for uppercase, lowercase, digit, special char
        has_upper = any(c.isupper() for c in new_password)
        has_lower = any(c.islower() for c in new_password)
        has_digit = any(c.isdigit() for c in new_password)
        has_special = any(
            c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in new_password)

        if not (has_upper and has_lower and has_digit and has_special):
            flash(
                'Password must contain uppercase, lowercase, digit, and special character', 'danger')
            return render_template('admin/change_password.html')

        # Don't allow same password
        if bcrypt.check_password_hash(current_user.password_hash, new_password):
            flash('New password must be different from current password', 'danger')
            return render_template('admin/change_password.html')

        # Update password
        try:
            current_user.password_hash = bcrypt.generate_password_hash(
                new_password).decode('utf-8')
            db.session.commit()

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
    return render_template('admin/users.html', users=users, now=datetime.utcnow())


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

        # Generate secure temporary password
        temp_password = generate_temp_password()

        # Create new user
        bcrypt = Bcrypt()
        new_user = User(
            username=username,
            email=email if email else None,
            role=role,
            password_hash=bcrypt.generate_password_hash(
                temp_password).decode('utf-8')
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            
            # Try to send email if email is provided (with error boundary)
            email_sent = False
            if email:
                try:
                    email_sent = send_password_email(email, username, temp_password)
                except Exception as e:
                    current_app.logger.error(f"Failed to send email after user creation: {str(e)}")
                    # Continue anyway - user was created successfully
                    pass

            # Show success page with password modal (instead of flash message)
            return render_template('admin/create_user_success.html',
                                 username=username,
                                 temp_password=temp_password,
                                 role=role,
                                 email=email,
                                 email_sent=email_sent)

        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user: {str(e)}', 'danger')
            return render_template('admin/create_user.html')

    return render_template('admin/create_user.html')


@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
@limiter.limit("30 per hour", methods=["POST"])
def reset_user_password(user_id):
    """Reset a user's password to a new temporary password"""
    user = User.query.get_or_404(user_id)

    # Generate new temporary password
    temp_password = generate_temp_password()

    # Update password
    bcrypt = Bcrypt()
    user.password_hash = bcrypt.generate_password_hash(
        temp_password).decode('utf-8')
    user.failed_login_attempts = 0  # Reset lockout counter
    user.locked_until = None  # Remove any lockout

    try:
        db.session.commit()
        
        # Try to send email if user has an email address (with error boundary)
        email_sent = False
        if user.email:
            try:
                email_sent = send_password_email(user.email, user.username, temp_password)
            except Exception as e:
                current_app.logger.error(f"Failed to send email after password reset: {str(e)}")
                # Continue anyway - password was reset successfully
                pass
        
        # Show success page with password modal (instead of flash message)
        return render_template('admin/create_user_success.html',
                             username=user.username,
                             temp_password=temp_password,
                             role=user.role,
                             email=user.email,
                             email_sent=email_sent,
                             is_reset=True)
    except Exception as e:
        db.session.rollback()
        flash(f'Error resetting password: {str(e)}', 'danger')
        return redirect(url_for('admin.manage_users'))


@admin_bp.route('/users/<int:user_id>/unlock', methods=['POST'])
@login_required
@admin_required
def unlock_user_account(user_id):
    """Unlock a locked user account"""
    user = User.query.get_or_404(user_id)

    user.failed_login_attempts = 0
    user.lockout_until = None

    try:
        db.session.commit()
        flash(f'Account unlocked for user "{user.username}"', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error unlocking account: {str(e)}', 'danger')

    return redirect(url_for('admin.manage_users'))


@admin_bp.route('/users/<int:user_id>/change-role', methods=['POST'])
@login_required
@admin_required
def change_user_role(user_id):
    """Change a user's role"""
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role', '')
    # Normalize to canonical capitalization
    new_role = (new_role or '').strip().capitalize()

    if new_role not in ['Admin', 'Supervisor', 'Champion']:
        flash('Invalid role selected', 'danger')
        return redirect(url_for('admin.manage_users'))

    old_role = user.role
    user.role = new_role

    try:
        db.session.commit()
        flash(
            f'Role changed for "{user.username}" from {old_role} to {new_role}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error changing role: {str(e)}', 'danger')

    return redirect(url_for('admin.manage_users'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user account"""
    user = User.query.get_or_404(user_id)

    # Prevent deleting your own account
    from flask_login import current_user
    if user.user_id == current_user.user_id:
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('admin.manage_users'))

    username = user.username

    try:
        db.session.delete(user)
        db.session.commit()
        flash(f'User "{username}" deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'danger')

    return redirect(url_for('admin.manage_users'))


@admin_bp.route('/champions/create', methods=['GET', 'POST'])
@login_required
@admin_required
@limiter.limit("15 per hour", methods=["POST"])
def create_champion():
    """Create a new champion with user account and profile"""
    if request.method == 'POST':
        # Debug: Log that we received a POST request
        print(f"DEBUG: POST request received from {current_user.username}")
        print(f"DEBUG: Form data keys: {list(request.form.keys())}")

        # Get form data
        username = request.form.get('username', '').strip()
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        gender = request.form.get('gender', '').strip()
        date_of_birth = request.form.get('date_of_birth', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        county_sub_county = request.form.get('county_sub_county', '').strip()
        supervisor_id = request.form.get('supervisor_id', '').strip()

        # Validation
        if not username or not full_name or not email or not phone_number:
            flash('Username, Full Name, Email, and Phone Number are required', 'danger')
            supervisors = User.query.filter_by(role=User.ROLE_SUPERVISOR).all()
            return render_template('admin/create_champion.html', supervisors=supervisors)

        if len(username) < 3:
            flash('Username must be at least 3 characters long', 'danger')
            supervisors = User.query.filter_by(role=User.ROLE_SUPERVISOR).all()
            return render_template('admin/create_champion.html', supervisors=supervisors)

        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash(
                f'Username "{username}" already exists. Please choose a different username.', 'danger')
            supervisors = User.query.filter_by(role=User.ROLE_SUPERVISOR).all()
            return render_template('admin/create_champion.html', supervisors=supervisors)

        # Check if email already exists
        if Champion.query.filter_by(email=email).first():
            flash(
                f'Email "{email}" already exists. Please use a different email.', 'danger')
            supervisors = User.query.filter_by(role=User.ROLE_SUPERVISOR).all()
            return render_template('admin/create_champion.html', supervisors=supervisors)

        # Check if phone number already exists
        if Champion.query.filter_by(phone_number=phone_number).first():
            flash(
                f'Phone number "{phone_number}" already exists. Please use a different phone number.', 'danger')
            supervisors = User.query.filter_by(role=User.ROLE_SUPERVISOR).all()
            return render_template('admin/create_champion.html', supervisors=supervisors)

        # Generate secure temporary password
        temp_password = generate_temp_password()

        try:
            # Create user account
            bcrypt = Bcrypt()
            new_user = User(username=username)
            new_user.set_role(User.ROLE_PREVENTION_ADVOCATE)  # Use constant to prevent typos
            new_user.password_hash = bcrypt.generate_password_hash(
                temp_password).decode('utf-8')
            db.session.add(new_user)
            db.session.flush()  # Get the user_id

            # Generate champion code (e.g., CH-001, CH-002)
            existing_count = Champion.query.count()
            champion_code = f"CH-{str(existing_count + 1).zfill(3)}"

            # Create champion profile with optional supervisor assignment
            new_champion = Champion(
                user_id=new_user.user_id,
                supervisor_id=int(supervisor_id) if supervisor_id else None,
                full_name=full_name,
                email=email,
                gender=gender if gender else None,
                date_of_birth=date_of_birth if date_of_birth else None,
                phone_number=phone_number,
                county_sub_county=county_sub_county if county_sub_county else None,
                assigned_champion_code=champion_code,
                application_status='Approved',
                champion_status='Active',
                risk_level='Low'
            )
            db.session.add(new_champion)
            db.session.flush()  # Get the champion_id

            # Link champion to user
            new_user.champion_id = new_champion.champion_id

            db.session.commit()

            # Try to send email synchronously (much more reliable than threading)
            email_sent = False
            if email:
                try:
                    current_app.logger.info(f"Attempting to send password email to {email}")
                    email_sent = send_password_email(email, username, temp_password)
                    
                    if email_sent:
                        current_app.logger.info(f"✅ Password email sent successfully to {email}")
                    else:
                        current_app.logger.warning(f"⚠️ Email sending failed for {email} - check email configuration")
                        
                except Exception as e:
                    current_app.logger.error(f"❌ Email exception for {email}: {str(e)}")
                    email_sent = False

            # Safe supervisor name retrieval
            supervisor_name = None
            if supervisor_id:
                try:
                    supervisor = User.query.get(int(supervisor_id))
                    if supervisor:
                        supervisor_name = supervisor.username
                except Exception:
                    pass

            # Show success page with password modal (instead of flash messages)
            return render_template('admin/create_user_success.html',
                                 username=username,
                                 temp_password=temp_password,
                                 role=User.ROLE_PREVENTION_ADVOCATE,
                                 email=email,
                                 email_sent=email_sent,
                                 is_champion=True,
                                 champion_code=champion_code,
                                 full_name=full_name,
                                 supervisor_username=supervisor_name)

        except IntegrityError as e:
            db.session.rollback()
            error_msg = str(e.orig)

            # Parse common constraint violations
            if 'phone_number' in error_msg and 'duplicate' in error_msg.lower():
                flash(
                    f'Phone number "{phone_number}" is already registered. Please use a different phone number.', 'danger')
            elif 'email' in error_msg and 'duplicate' in error_msg.lower():
                flash(
                    f'Email "{email}" is already registered. Please use a different email.', 'danger')
            elif 'username' in error_msg and 'duplicate' in error_msg.lower():
                flash(
                    f'Username "{username}" is already taken. Please choose a different username.', 'danger')
            else:
                flash(
                    f'A champion with this information already exists. Please check phone number, email, and username.', 'danger')

            supervisors = User.query.filter_by(role=User.ROLE_SUPERVISOR).all()
            return render_template('admin/create_champion.html', supervisors=supervisors)

        except Exception as e:
            db.session.rollback()
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

    champion = Champion.query.get_or_404(champion_id)

    try:
        if supervisor_id:
            # Assign to supervisor (with safe lookup)
            supervisor = User.query.get(int(supervisor_id))
            if not supervisor or supervisor.role != 'Supervisor':
                flash('Invalid supervisor selected', 'danger')
                return redirect(url_for('admin.manage_assignments'))

            old_supervisor_id = champion.supervisor_id
            champion.supervisor_id = int(supervisor_id)

            # Safe lookup of old supervisor name
            old_supervisor_name = "Unknown"
            if old_supervisor_id:
                old_supervisor = User.query.get(old_supervisor_id)
                if old_supervisor:
                    old_supervisor_name = old_supervisor.username
                flash(
                    f'Champion {champion.assigned_champion_code} reassigned from {old_supervisor_name} to {supervisor.username}', 'success')
            else:
                flash(
                    f'Champion {champion.assigned_champion_code} assigned to {supervisor.username}', 'success')
        else:
            # Unassign from supervisor (with safe lookup)
            supervisor_name = "supervisor"
            if champion.supervisor_id:
                old_supervisor = User.query.get(champion.supervisor_id)
                if old_supervisor:
                    supervisor_name = old_supervisor.username
                flash(
                    f'Champion {champion.assigned_champion_code} unassigned from {supervisor_name}', 'info')
            champion.supervisor_id = None

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        flash(f'Error updating assignment: {str(e)}', 'danger')

    return redirect(url_for('admin.manage_assignments'))


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
        registration = MemberRegistration.query.get_or_404(registration_id)
        
        if registration.status != 'Pending':
            flash('Registration has already been processed.', 'warning')
            return redirect(url_for('admin.registrations'))
        
        # Create user account
        user = User(username=registration.username)
        user.set_role(User.ROLE_PREVENTION_ADVOCATE)  # Use constant to prevent typos
        user.password_hash = registration.password_hash
        
        db.session.add(user)
        db.session.flush()
        
        # Update registration
        registration.status = 'Approved'
        registration.reviewed_at = datetime.utcnow()
        registration.reviewed_by = current_user.user_id
        registration.created_user_id = user.user_id
        
        db.session.commit()
        
        flash(f'Registration for {registration.full_name} ({registration.username}) has been approved!', 'success')
        return redirect(url_for('admin.registrations'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error approving registration: {str(e)}', 'danger')
        return redirect(url_for('admin.registrations'))


@admin_bp.route('/registrations/<int:registration_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_registration_web(registration_id):
    """Reject a registration from the web interface"""
    try:
        registration = MemberRegistration.query.get_or_404(registration_id)
        
        if registration.status != 'Pending':
            flash('Registration has already been processed.', 'warning')
            return redirect(url_for('admin.registrations'))
        
        reason = request.form.get('reason', 'No reason provided')
        
        registration.status = 'Rejected'
        registration.reviewed_at = datetime.utcnow()
        registration.reviewed_by = current_user.user_id
        registration.rejection_reason = reason
        
        db.session.commit()
        
        flash(f'Registration for {registration.full_name} has been rejected.', 'info')
        return redirect(url_for('admin.registrations'))
        
    except Exception as e:
        db.session.rollback()
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
        application = ChampionApplication.query.get_or_404(application_id)
        
        if application.status != 'Pending':
            flash('Application has already been processed.', 'warning')
            return redirect(url_for('admin.champion_applications'))
        
        assigned_champion_code = request.form.get('champion_code')
        
        if not assigned_champion_code:
            flash('Champion code is required.', 'danger')
            return redirect(url_for('admin.champion_applications'))
        
        # Check if champion code already exists
        if Champion.query.filter_by(assigned_champion_code=assigned_champion_code).first():
            flash('Champion code already exists. Please use a unique code.', 'danger')
            return redirect(url_for('admin.champion_applications'))
        
        # Create champion profile
        champion = Champion(
            user_id=application.user_id,
            full_name=application.full_name,
            email=application.email,
            phone_number=application.phone_number,
            alternative_phone_number=application.alternative_phone_number,
            gender=application.gender,
            date_of_birth=application.date_of_birth,
            county_sub_county=application.county_sub_county,
            assigned_champion_code=assigned_champion_code,
            emergency_contact_name=application.emergency_contact_name,
            emergency_contact_relationship=application.emergency_contact_relationship,
            emergency_contact_phone=application.emergency_contact_phone,
            current_education_level=application.current_education_level,
            education_institution_name=application.education_institution_name,
            course_field_of_study=application.course_field_of_study,
            year_of_study=application.year_of_study,
            workplace_organization=application.workplace_organization,
            date_of_application=datetime.utcnow().date(),
            application_status='Recruited',
            champion_status='Active'
        )
        
        db.session.add(champion)
        db.session.flush()
        
        # Update user to link champion profile (with safe lookup)
        user = User.query.get(application.user_id)
        if not user:
            raise ValueError(f"User with ID {application.user_id} not found")
        user.champion_id = champion.champion_id
        
        # Update application
        application.status = 'Approved'
        application.reviewed_at = datetime.utcnow()
        application.reviewed_by = current_user.user_id
        application.created_champion_id = champion.champion_id
        
        db.session.commit()
        
        flash(f'Champion application for {application.full_name} has been approved! Champion code: {assigned_champion_code}', 'success')
        return redirect(url_for('admin.champion_applications'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error approving application: {str(e)}', 'danger')
        return redirect(url_for('admin.champion_applications'))


@admin_bp.route('/champion-applications/<int:application_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_application_web(application_id):
    """Reject a champion application from the web interface"""
    try:
        application = ChampionApplication.query.get_or_404(application_id)
        
        if application.status != 'Pending':
            flash('Application has already been processed.', 'warning')
            return redirect(url_for('admin.champion_applications'))
        
        reason = request.form.get('reason', 'No reason provided')
        
        application.status = 'Rejected'
        application.reviewed_at = datetime.utcnow()
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
        now=datetime.utcnow()
    )


@admin_bp.route('/debates/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_debate_event():
    """Create a new Debaters Circle event"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        motion = request.form.get('motion', '').strip()
        event_date_raw = request.form.get('event_date', '').strip()
        if not title or not motion or not event_date_raw:
            flash('Title, motion, and event date are required.', 'danger')
            return render_template('admin/debate_event_form.html', action='Create', event=None)

        try:
            event_date = datetime.strptime(event_date_raw, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date format. Please use the provided date picker.', 'danger')
            return render_template('admin/debate_event_form.html', action='Create', event=None)

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
            return render_template('admin/debate_event_form.html', action='Create', event=None)

        event = Event(
            title=title,
            description=request.form.get('description'),
            event_date=event_date,
            location=request.form.get('location'),
            event_type='debate',
            organizer=request.form.get('organizer'),
            max_participants=max_participants,
            registration_deadline=registration_deadline,
            status=request.form.get('status', 'Upcoming'),
            image_url=request.form.get('image_url'),
            motion=motion,
            created_by=current_user.user_id
        )

        db.session.add(event)
        db.session.commit()

        flash('Debaters Circle event created.', 'success')
        return redirect(url_for('admin.debates'))

    return render_template('admin/debate_event_form.html', action='Create', event=None)


@admin_bp.route('/debates/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_debate_event(event_id):
    """Edit an existing Debaters Circle event"""
    event = Event.query.get_or_404(event_id)
    if event.event_type not in ['debate', 'Debaters Circle']:
        flash('This event is not part of Debaters Circle.', 'warning')
        return redirect(url_for('admin.debates'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        motion = request.form.get('motion', '').strip()
        event_date_raw = request.form.get('event_date', '').strip()
        if not title or not motion or not event_date_raw:
            flash('Title, motion, and event date are required.', 'danger')
            return render_template('admin/debate_event_form.html', action='Edit', event=event)

        try:
            event_date = datetime.strptime(event_date_raw, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date format. Please use the provided date picker.', 'danger')
            return render_template('admin/debate_event_form.html', action='Edit', event=event)

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
            return render_template('admin/debate_event_form.html', action='Edit', event=event)

        event.title = title
        event.description = request.form.get('description')
        event.event_date = event_date
        event.location = request.form.get('location')
        event.organizer = request.form.get('organizer')
        event.max_participants = max_participants
        event.registration_deadline = registration_deadline
        event.status = request.form.get('status', 'Upcoming')
        event.image_url = request.form.get('image_url')
        event.motion = motion
        event.updated_at = datetime.utcnow()

        db.session.commit()

        flash('Debaters Circle event updated.', 'success')
        return redirect(url_for('admin.debates'))

    return render_template('admin/debate_event_form.html', action='Edit', event=event)


@admin_bp.route('/debates/<int:event_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_debate_event(event_id):
    """Delete a Debaters Circle event"""
    event = Event.query.get_or_404(event_id)
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
        now=datetime.utcnow()
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
    event = Event.query.get_or_404(event_id)
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
        event.updated_at = datetime.utcnow()

        db.session.commit()

        flash('Campus Edition event updated.', 'success')
        return redirect(url_for('admin.campus_edition'))

    return render_template('admin/campus_event_form.html', action='Edit', event=event)


@admin_bp.route('/campus-edition/<int:event_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_campus_event(event_id):
    """Delete a Campus Edition event"""
    event = Event.query.get_or_404(event_id)
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
    from models import SeedFundingApplication
    
    status_filter = request.args.get('status', 'all')
    
    query = SeedFundingApplication.query
    if status_filter != 'all' and status_filter:
        query = query.filter_by(status=status_filter)
    
    applications = query.order_by(SeedFundingApplication.submitted_at.desc()).all()
    
    # Get statistics
    total = SeedFundingApplication.query.count()
    pending = SeedFundingApplication.query.filter_by(status='Pending').count()
    under_review = SeedFundingApplication.query.filter_by(status='Under Review').count()
    approved = SeedFundingApplication.query.filter_by(status='Approved').count()
    rejected = SeedFundingApplication.query.filter_by(status='Rejected').count()
    funded = SeedFundingApplication.query.filter_by(status='Funded').count()
    
    # Calculate total amounts
    from sqlalchemy import func
    total_requested = db.session.query(
        func.sum(SeedFundingApplication.total_budget_requested)
    ).scalar() or 0
    
    total_approved = db.session.query(
        func.sum(SeedFundingApplication.approved_amount)
    ).filter(
        SeedFundingApplication.status.in_(['Approved', 'Funded'])
    ).scalar() or 0
    
    stats = {
        'total': total,
        'pending': pending,
        'under_review': under_review,
        'approved': approved,
        'rejected': rejected,
        'funded': funded,
        'total_requested': float(total_requested) if total_requested else 0,
        'total_approved': float(total_approved) if total_approved else 0
    }
    
    return render_template(
        'admin/seed_funding_list.html',
        applications=applications,
        status_filter=status_filter,
        stats=stats,
        now=datetime.utcnow()
    )


@admin_bp.route('/seed-funding/<int:application_id>')
@login_required
@admin_required
def seed_funding_detail(application_id):
    """View detailed seed funding application"""
    from models import SeedFundingApplication
    
    application = SeedFundingApplication.query.get_or_404(application_id)
    
    return render_template(
        'admin/seed_funding_detail.html',
        application=application
    )


@admin_bp.route('/seed-funding/<int:application_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_seed_funding(application_id):
    """Approve a seed funding application"""
    from models import SeedFundingApplication
    
    application = SeedFundingApplication.query.get_or_404(application_id)
    
    approved_amount = request.form.get('approved_amount')
    approval_conditions = request.form.get('approval_conditions', '').strip()
    admin_notes = request.form.get('admin_notes', '').strip()
    
    if not approved_amount:
        flash('Approved amount is required.', 'danger')
        return redirect(url_for('admin.seed_funding_detail', application_id=application_id))
    
    try:
        application.status = 'Approved'
        application.approved_amount = float(approved_amount)
        application.approval_conditions = approval_conditions if approval_conditions else None
        application.admin_notes = admin_notes if admin_notes else None
        application.reviewed_at = datetime.utcnow()
        application.reviewed_by = current_user.user_id
        
        db.session.commit()
        flash(f'Seed funding application approved with KES {approved_amount:,.2f}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error approving application: {str(e)}', 'danger')
    
    return redirect(url_for('admin.seed_funding_detail', application_id=application_id))


@admin_bp.route('/seed-funding/<int:application_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_seed_funding(application_id):
    """Reject a seed funding application"""
    from models import SeedFundingApplication
    
    application = SeedFundingApplication.query.get_or_404(application_id)
    
    rejection_reason = request.form.get('rejection_reason', '').strip()
    admin_notes = request.form.get('admin_notes', '').strip()
    
    if not rejection_reason:
        flash('Rejection reason is required.', 'danger')
        return redirect(url_for('admin.seed_funding_detail', application_id=application_id))
    
    application.status = 'Rejected'
    application.rejection_reason = rejection_reason
    application.admin_notes = admin_notes if admin_notes else None
    application.reviewed_at = datetime.utcnow()
    application.reviewed_by = current_user.user_id
    
    db.session.commit()
    flash('Seed funding application rejected.', 'success')
    
    return redirect(url_for('admin.seed_funding_detail', application_id=application_id))


@admin_bp.route('/seed-funding/<int:application_id>/mark-funded', methods=['POST'])
@login_required
@admin_required
def mark_seed_funding_funded(application_id):
    """Mark a seed funding application as funded (disbursed)"""
    from models import SeedFundingApplication
    
    application = SeedFundingApplication.query.get_or_404(application_id)
    
    if application.status != 'Approved':
        flash('Only approved applications can be marked as funded.', 'warning')
        return redirect(url_for('admin.seed_funding_detail', application_id=application_id))
    
    disbursement_date_raw = request.form.get('disbursement_date', '').strip()
    disbursement_method = request.form.get('disbursement_method', '').strip()
    disbursement_reference = request.form.get('disbursement_reference', '').strip()
    
    if not disbursement_date_raw or not disbursement_method:
        flash('Disbursement date and method are required.', 'danger')
        return redirect(url_for('admin.seed_funding_detail', application_id=application_id))
    
    try:
        disbursement_date = datetime.strptime(disbursement_date_raw, '%Y-%m-%d').date()
        
        application.status = 'Funded'
        application.disbursement_date = disbursement_date
        application.disbursement_method = disbursement_method
        application.disbursement_reference = disbursement_reference if disbursement_reference else None
        
        db.session.commit()
        flash('Application marked as funded.', 'success')
        
    except ValueError:
        flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error marking as funded: {str(e)}', 'danger')
    
    return redirect(url_for('admin.seed_funding_detail', application_id=application_id))


@admin_bp.route('/seed-funding/<int:application_id>/update-review-status', methods=['POST'])
@login_required
@admin_required
def update_seed_funding_review_status(application_id):
    """Update seed funding application to Under Review"""
    from models import SeedFundingApplication
    
    application = SeedFundingApplication.query.get_or_404(application_id)
    
    application.status = 'Under Review'
    application.reviewed_at = datetime.utcnow()
    application.reviewed_by = current_user.user_id
    
    admin_notes = request.form.get('admin_notes', '').strip()
    if admin_notes:
        application.admin_notes = admin_notes
    
    db.session.commit()
    flash('Application moved to Under Review.', 'success')
    
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
        now=datetime.utcnow()
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
    event = Event.query.get_or_404(event_id)
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
        event.updated_at = datetime.utcnow()

        db.session.commit()

        flash('UMV Mtaani event updated.', 'success')
        return redirect(url_for('admin.umv_mtaani'))

    return render_template('admin/mtaani_event_form.html', action='Edit', event=event)


@admin_bp.route('/umv-mtaani/<int:event_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_mtaani_event(event_id):
    """Delete a UMV Mtaani event"""
    event = Event.query.get_or_404(event_id)
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
            # Get form data
            title = request.form.get('title')
            description = request.form.get('description')
            guest = request.form.get('guest')
            audio_url = request.form.get('audio_url')
            thumbnail_url = request.form.get('thumbnail_url')
            duration = request.form.get('duration')
            episode_number = request.form.get('episode_number')
            season_number = request.form.get('season_number')
            category = request.form.get('category')
            tags_str = request.form.get('tags', '')
            published = request.form.get('published') == 'on'
            
            # Parse tags
            tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
            
            # Create podcast
            podcast = Podcast(
                title=title,
                description=description,
                guest=guest,
                audio_url=audio_url,
                thumbnail_url=thumbnail_url,
                duration=int(duration) if duration else None,
                episode_number=int(episode_number) if episode_number else None,
                season_number=int(season_number) if season_number else None,
                category=category if category else None,
                tags=tags,
                published=published,
                created_by=current_user.user_id
            )
            
            if published:
                podcast.published_at = datetime.utcnow()
            
            db.session.add(podcast)
            db.session.commit()
            
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
    podcast = Podcast.query.get_or_404(podcast_id)
    
    if request.method == 'POST':
        try:
            # Update fields
            podcast.title = request.form.get('title')
            podcast.description = request.form.get('description')
            podcast.guest = request.form.get('guest')
            podcast.audio_url = request.form.get('audio_url')
            podcast.thumbnail_url = request.form.get('thumbnail_url')
            
            duration = request.form.get('duration')
            podcast.duration = int(duration) if duration else None
            
            episode_number = request.form.get('episode_number')
            podcast.episode_number = int(episode_number) if episode_number else None
            
            season_number = request.form.get('season_number')
            podcast.season_number = int(season_number) if season_number else None
            
            category = request.form.get('category')
            podcast.category = category if category else None
            
            tags_str = request.form.get('tags', '')
            podcast.tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
            
            was_published = podcast.published
            podcast.published = request.form.get('published') == 'on'
            
            # Set published_at when first publishing
            if not was_published and podcast.published:
                podcast.published_at = datetime.utcnow()
            
            podcast.updated_at = datetime.utcnow()
            
            db.session.commit()
            
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
        podcast = Podcast.query.get_or_404(podcast_id)
        db.session.delete(podcast)
        db.session.commit()
        
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
        podcast = Podcast.query.get_or_404(podcast_id)
        
        was_published = podcast.published
        podcast.published = not podcast.published
        
        # Set published_at when first publishing
        if not was_published and podcast.published:
            podcast.published_at = datetime.utcnow()
        
        podcast.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        status = 'published' if podcast.published else 'unpublished'
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
    
    workstreams_data = [
        {
            'id': 'podcasts',
            'name': 'Podcasts',
            'description': 'Manage podcast episodes and guests',
            'icon': '🎙️',
            'route': 'admin.podcasts',
            'create_route': 'admin.create_podcast',
            'count': Podcast.query.count()
        },
        {
            'id': 'debators_circle',
            'name': 'Debators Circle',
            'description': 'Manage debate events and champion participation',
            'icon': '🎤',
            'route': 'admin.debates',
            'create_route': 'admin.create_debate_event',
            'count': Event.query.filter(Event.event_type.in_(['debate', 'Debaters Circle'])).count()
        },
        {
            'id': 'campus_edition',
            'name': 'Campus Edition',
            'description': 'Manage campus-based events and activities',
            'icon': '🎓',
            'route': 'admin.campus_edition',
            'create_route': 'admin.create_campus_event',
            'count': Event.query.filter(Event.event_type == 'campus').count()
        },
        {
            'id': 'seed_funding',
            'name': 'Seed Funding',
            'description': 'Review and approve seed funding applications',
            'icon': '💰',
            'route': 'admin.seed_funding_applications',
            'create_route': None,  # Applications come from frontend
            'count': SeedFundingApplication.query.count()
        },
        {
            'id': 'umv_mtaani',
            'name': 'UMV Mtaani',
            'description': 'Manage community barazas and mtaani events',
            'icon': '🏘️',
            'route': 'admin.umv_mtaani',
            'create_route': 'admin.create_mtaani_event',
            'count': Event.query.filter(Event.event_type == 'mtaani').count()
        }
    ]
    
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
    affirmation = DailyAffirmation.query.get_or_404(affirmation_id)
    
    if request.method == 'POST':
        affirmation.content = request.form.get('content', '').strip()
        affirmation.theme = request.form.get('theme', 'General').strip()
        scheduled_date = request.form.get('scheduled_date', '').strip()
        affirmation.active = request.form.get('active') == 'on'
        affirmation.updated_at = datetime.utcnow()
        
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
        affirmation = DailyAffirmation.query.get_or_404(affirmation_id)
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
    item = SymbolicItem.query.get_or_404(item_id)
    
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
        item = SymbolicItem.query.get_or_404(item_id)
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
    assessment = MentalHealthAssessment.query.get_or_404(assessment_id)
    
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
        
        try:
            current_app.logger.info(f"Admin {current_user.username} testing email to {test_recipient}")
            email_sent = send_password_email(
                recipient_email=test_recipient,
                username="test_user",
                temp_password="TestPass123!"
            )
            
            if email_sent:
                flash(f'✅ Test email sent successfully to {test_recipient}. Check inbox and spam folder.', 'success')
            else:
                flash(f'❌ Email sending failed. Check server logs for details.', 'danger')
                
        except Exception as e:
            current_app.logger.error(f"Email test error: {str(e)}")
            flash(f'❌ Email error: {str(e)}', 'danger')
        
        return redirect(url_for('admin.test_email'))
    
    # GET request - show email config
    config_status = {
        'MAIL_SERVER': current_app.config.get('MAIL_SERVER'),
        'MAIL_PORT': current_app.config.get('MAIL_PORT'),
        'MAIL_USE_TLS': current_app.config.get('MAIL_USE_TLS'),
        'MAIL_USERNAME': current_app.config.get('MAIL_USERNAME'),
        'MAIL_PASSWORD': '✓ Set' if current_app.config.get('MAIL_PASSWORD') else '✗ Missing',
        'MAIL_DEFAULT_SENDER': current_app.config.get('MAIL_DEFAULT_SENDER'),
    }
    
    return render_template('admin/test_email.html', config=config_status)
