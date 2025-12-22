from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user, login_required
from models import db, User, Champion
from decorators import admin_required, supervisor_required, champion_required
from extensions import limiter
from password_validator import validate_password_strength
from datetime import datetime

auth_bp = Blueprint('auth', __name__, template_folder='templates')

# --- Helper function for password hashing/checking is in models.py ---
@auth_bp.route('/register', methods=['GET', 'POST'])
@admin_required  # Only an Admin can register new users
def register():
    if request.method == 'POST':
        # Get password and validate strength
        password = request.form.get('password')
        is_valid, error_message = validate_password_strength(password)
        if not is_valid:
            flash(error_message, 'danger')
            return redirect(url_for('auth.register'))
        
        # Create Champion Profile (Initial Static Data)
        champion = Champion(
            full_name=request.form.get('full_name'),
            email=request.form.get('email'),
            phone_number=request.form.get('phone_number'),
            assigned_champion_code=request.form.get('assigned_champion_code'),
        )
        db.session.add(champion)
        db.session.commit()

        # Create User Login Account
        username = request.form.get('username')
        role = request.form.get('role', 'Champion')  # Default to Champion
        role = role.capitalize()

        # Check for existing username/email
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('auth.register'))

        user = User(
            username=username,
            role=role,
            champion_id=champion.champion_id if role == 'Champion' else None
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Update Champion FK link if the user is a Champion
        if role == 'Champion':
            champion.user_id = user.user_id  # Link Champion to newly created User
            db.session.commit()

        flash(f'New {role} account for {champion.full_name} created successfully.', 'success')
        return redirect(url_for('main.index'))

    # Simple form rendering for GET request (test-friendly placeholder)
    # In production this should render a proper template.
    if request.method == 'GET':
        return 'Registration form'


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute", methods=["POST"], exempt_when=lambda: False)
def login():
    if current_user.is_authenticated:
        # Redirect authenticated users directly to their role dashboard (case-insensitive)
        role_lower = (current_user.role or '').lower()
        if role_lower == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif role_lower == 'supervisor':
            return redirect(url_for('supervisor.dashboard'))
        elif role_lower == 'champion':
            return redirect(url_for('champion.dashboard'))
        else:
            return redirect(url_for('auth.login'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user:
            # Check if account is locked
            if user.is_locked():
                remaining_time = int((user.locked_until - datetime.utcnow()).total_seconds() / 60)
                flash(f'Account is locked due to too many failed login attempts. Please try again in {remaining_time} minutes.', 'danger')
                return render_template('auth/login.html')
            
            # Check password
            if user.check_password(password):
                # Successful login - reset failed attempts
                user.reset_failed_logins()
                login_user(user, remember=True)
                flash('Logged in successfully', 'success')
                # Redirect directly to role-specific dashboard (case-insensitive)
                role_lower = (user.role or '').lower()
                if role_lower == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif role_lower == 'supervisor':
                    return redirect(url_for('supervisor.dashboard'))
                elif role_lower == 'champion':
                    return redirect(url_for('champion.dashboard'))
                else:
                    return redirect(url_for('auth.login'))
            else:
                # Failed login - record attempt
                user.record_failed_login()
                remaining_attempts = 7 - (user.failed_login_attempts or 0)
                if remaining_attempts > 0:
                    flash(f'Invalid username or password. {remaining_attempts} attempts remaining before account lockout.', 'danger')
                else:
                    flash('Account locked due to too many failed login attempts. Please try again in 30 minutes.', 'danger')
        else:
            # Username not found - don't reveal this info
            flash('Invalid username or password', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))



