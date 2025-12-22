from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func
from models import db, Champion, YouthSupport, RefferalPathway, TrainingRecord, get_champions_needing_refresher, get_high_risk_champions, get_overdue_reviews, User
from decorators import admin_required
from flask_bcrypt import Bcrypt
import secrets
import string
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # HIGH-LEVEL DASHBOARD METRICS

    # CHAMPION STATUS TRACKING
    total_champions = Champion.query.count()
    active_champions = Champion.query.filter_by(champion_status='Active').count()
    inactive_champions = Champion.query.filter_by(champion_status='Inactive').count()
    on_hold_champions = Champion.query.filter_by(champion_status='On Hold').count()

    # 1. Average Check-In Completion Rate
    # This calculates the rounded average of all weekly check-in completion rates
    average_check_in = db.session.query(func.avg(YouthSupport.weekly_check_in_completion_rate)).scalar() or 0
    avg_check_in_rounded = round(average_check_in, 0)  # Rounded to nearest percentage
    
    # 1b. Average Mini-Screening Completion Rate
    # Calculate percentage of mini-screenings completed vs expected
    total_expected_screenings = db.session.query(func.count(YouthSupport.support_id)).scalar() or 0
    total_completed_screenings = db.session.query(func.sum(YouthSupport.monthly_mini_screenings_delivered)).scalar() or 0
    avg_screening_completion_rate = (total_completed_screenings / total_expected_screenings) if total_expected_screenings > 0 else 0

    # 2. Referral Conversion Rate (Success Rate)
    # Ratio of "Attended" outcomes vs total referrals
    total_referrals = RefferalPathway.query.count()
    successful_referrals = RefferalPathway.query.filter_by(referal_outcomes='Attended').count()
    conversion_rate = (successful_referrals / total_referrals * 100) if total_referrals > 0 else 0

    # 3. Training Compliance Rate
    # Percentage of champions with "Certified" status for core modules
    total_training_records = TrainingRecord.query.count()
    certified_records = TrainingRecord.query.filter_by(certification_status='Certified').count()
    training_compliance_rate = (certified_records / total_training_records * 100) if total_training_records > 0 else 0

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
            func.coalesce(func.max(YouthSupport.number_of_youth_under_support), 0).label('total_youth')
        )
        .outerjoin(YouthSupport)
        .group_by(Champion.champion_id, Champion.full_name, Champion.assigned_champion_code)
        .all()
    )
    
    # Total youth reached across all champions
    total_youth_reached = db.session.query(func.sum(YouthSupport.number_of_youth_under_support)).scalar() or 0

    # 5. Quarterly Satisfaction Score
    # Average of youth feedback scores (self_reported_wellbeing_check)
    quarterly_satisfaction = db.session.query(func.avg(YouthSupport.self_reported_wellbeing_check)).scalar() or 0
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
    avg_flag_to_referral = db.session.query(func.avg(RefferalPathway.flag_to_referral_days)).scalar() or 0
    avg_flag_to_referral_rounded = round(avg_flag_to_referral, 1)

    # CONSENT & LEGAL COMPLIANCE CHECK
    champions_missing_consent = Champion.query.filter_by(consent_obtained=False).count()
    champions_missing_institution = Champion.query.filter_by(institution_consent_obtained=False).count()

    # REFRESHER ALERTS (next 30 days)
    upcoming_refreshers = get_champions_needing_refresher(days_ahead=30)

    return render_template('admin/dashboard.html',
        # Champion Status Counts
        total_champions=total_champions,
        active_champions=active_champions,
        inactive_champions=inactive_champions,
        on_hold_champions=on_hold_champions,
        
        # Performance Metrics
        avg_check_in=avg_check_in_rounded,
        avg_screening_completion_rate=round(avg_screening_completion_rate, 1),
        conversion_rate=round(conversion_rate, 1),
        training_compliance_rate=round(training_compliance_rate, 1),
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
        overdue_count=len(get_overdue_reviews())
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
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in new_password)
        
        if not (has_upper and has_lower and has_digit and has_special):
            flash('Password must contain uppercase, lowercase, digit, and special character', 'danger')
            return render_template('admin/change_password.html')
        
        # Don't allow same password
        if bcrypt.check_password_hash(current_user.password_hash, new_password):
            flash('New password must be different from current password', 'danger')
            return render_template('admin/change_password.html')
        
        # Update password
        try:
            current_user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
            db.session.commit()
            
            flash('Password changed successfully!', 'success')
            flash('You can now use your new password on next login.', 'info')
            
            # Redirect based on role (case-insensitive)
            role_lower = (current_user.role or '').lower()
            if role_lower == 'admin':
                return redirect(url_for('admin.settings'))
            elif role_lower == 'supervisor':
                return redirect(url_for('supervisor.dashboard'))
            elif role_lower == 'champion':
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
def create_user():
    """Create a new user account"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
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
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash(f'Username "{username}" already exists. Please choose a different username.', 'danger')
            return render_template('admin/create_user.html')
        
        # Generate secure temporary password
        temp_password = generate_temp_password()
        
        # Create new user
        bcrypt = Bcrypt()
        new_user = User(
            username=username,
            role=role,
            password_hash=bcrypt.generate_password_hash(temp_password).decode('utf-8')
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            
            # Show success message with temporary password
            flash(f'User "{username}" created successfully!', 'success')
            flash(f'Temporary Password: {temp_password}', 'info')
            flash('Please provide this password to the user securely. They should change it on first login.', 'warning')
            
            return redirect(url_for('admin.manage_users'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user: {str(e)}', 'danger')
            return render_template('admin/create_user.html')
    
    return render_template('admin/create_user.html')


@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_user_password(user_id):
    """Reset a user's password to a new temporary password"""
    user = User.query.get_or_404(user_id)
    
    # Generate new temporary password
    temp_password = generate_temp_password()
    
    # Update password
    bcrypt = Bcrypt()
    user.password_hash = bcrypt.generate_password_hash(temp_password).decode('utf-8')
    user.failed_login_attempts = 0  # Reset lockout counter
    user.locked_until = None  # Remove any lockout
    
    try:
        db.session.commit()
        flash(f'Password reset for user "{user.username}"', 'success')
        flash(f'New Temporary Password: {temp_password}', 'info')
        flash('Please provide this password to the user securely.', 'warning')
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
        flash(f'Role changed for "{user.username}" from {old_role} to {new_role}', 'success')
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
def create_champion():
    """Create a new champion with user account and profile"""
    if request.method == 'POST':
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
            supervisors = User.query.filter_by(role='Supervisor').all()
            return render_template('admin/create_champion.html', supervisors=supervisors)
        
        if len(username) < 3:
            flash('Username must be at least 3 characters long', 'danger')
            supervisors = User.query.filter_by(role='Supervisor').all()
            return render_template('admin/create_champion.html', supervisors=supervisors)
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash(f'Username "{username}" already exists. Please choose a different username.', 'danger')
            supervisors = User.query.filter_by(role='Supervisor').all()
            return render_template('admin/create_champion.html', supervisors=supervisors)
        
        # Check if email already exists
        if Champion.query.filter_by(email=email).first():
            flash(f'Email "{email}" already exists. Please use a different email.', 'danger')
            supervisors = User.query.filter_by(role='Supervisor').all()
            return render_template('admin/create_champion.html', supervisors=supervisors)
        
        # Generate secure temporary password
        temp_password = generate_temp_password()
        
        try:
            # Create user account
            bcrypt = Bcrypt()
            new_user = User(
                username=username,
                role='Champion',
                password_hash=bcrypt.generate_password_hash(temp_password).decode('utf-8')
            )
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
            
            # Show success message with temporary password
            flash(f'Champion "{full_name}" ({champion_code}) created successfully!', 'success')
            if supervisor_id:
                supervisor = User.query.get(int(supervisor_id))
                if supervisor:
                    flash(f'Assigned to supervisor: {supervisor.username}', 'info')
            flash(f'Username: {username} | Temporary Password: {temp_password}', 'info')
            flash('Please provide these credentials to the champion securely. They should change the password on first login.', 'warning')
            
            return redirect(url_for('supervisor.dashboard'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating champion: {str(e)}', 'danger')
            supervisors = User.query.filter_by(role='Supervisor').all()
            return render_template('admin/create_champion.html', supervisors=supervisors)
    
    # GET request - show form with supervisors list
    supervisors = User.query.filter_by(role='Supervisor').all()
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
    
    supervisors = User.query.filter_by(role='Supervisor').all()
    
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
            # Assign to supervisor
            supervisor = User.query.get(int(supervisor_id))
            if not supervisor or supervisor.role != 'Supervisor':
                flash('Invalid supervisor selected', 'danger')
                return redirect(url_for('admin.manage_assignments'))
            
            old_supervisor_id = champion.supervisor_id
            champion.supervisor_id = int(supervisor_id)
            
            if old_supervisor_id:
                old_supervisor = User.query.get(old_supervisor_id)
                flash(f'Champion {champion.assigned_champion_code} reassigned from {old_supervisor.username if old_supervisor else "Unknown"} to {supervisor.username}', 'success')
            else:
                flash(f'Champion {champion.assigned_champion_code} assigned to {supervisor.username}', 'success')
        else:
            # Unassign from supervisor
            if champion.supervisor_id:
                old_supervisor = User.query.get(champion.supervisor_id)
                flash(f'Champion {champion.assigned_champion_code} unassigned from {old_supervisor.username if old_supervisor else "supervisor"}', 'info')
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
