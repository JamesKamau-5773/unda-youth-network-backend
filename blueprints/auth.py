from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user, login_required
from models import db, User, Champion
from decorators import admin_required, supervisor_required, champion_required
from extensions import limiter

auth_bp = Blueprint('auth', __name__, template_folder='templates')

# --- Helper function for password hashing/checking is in models.py ---
@auth_bp.route('/register', methods=['GET', 'POST'])
@admin_required  # Only an Admin can register new users
def register():
    if request.method == 'POST':
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
        password = request.form.get('password')
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
@limiter.limit("4 per minute", methods=["POST"], exempt_when=lambda: False)
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard_redirect'))  # Redirect if already logged in

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            flash('Logged in successfully', 'success')

            # Redirect user based on their role after successful login
            return redirect(url_for('main.dashboard_redirect'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))


# Minimal role dashboards so redirects have targets
@auth_bp.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    return render_template('admin/dashboard.html') if False else 'Admin dashboard'


@auth_bp.route('/supervisor/dashboard')
@login_required
@supervisor_required
def supervisor_dashboard():
    return render_template('supervisor/dashboard.html') if False else 'Supervisor dashboard'


@auth_bp.route('/champion/dashboard')
@login_required
@champion_required
def champion_dashboard():
    return render_template('champion/dashboard.html') if False else 'Champion dashboard'
