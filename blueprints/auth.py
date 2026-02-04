from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, current_user, login_required
from models import db, User, Champion, MemberRegistration
from models import RefreshToken
from decorators import admin_required, supervisor_required, champion_required
from extensions import limiter
from password_validator import validate_password_strength
from datetime import datetime, timezone
from metrics import track_login_attempt
import os
import jwt
import hashlib
import secrets
from datetime import timedelta
from flask import jsonify, make_response

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
        # Create a MemberRegistration record for public signup.
        # Email is optional at signup; username is auto-generated from first name.
        full_name = request.form.get('full_name') or ''
        email = request.form.get('email') or None
        phone = request.form.get('phone_number')

        # Auto-generate a username base from the first name
        base = ''.join(ch for ch in (full_name.split()[0] if full_name else 'user').lower() if ch.isalnum()) or 'user'
        username_candidate = base
        idx = 1
        while User.query.filter_by(username=username_candidate).first() or MemberRegistration.query.filter_by(username=username_candidate).first():
            idx += 1
            username_candidate = f"{base}{idx}"

        registration = MemberRegistration(
            full_name=full_name,
            email=email,
            phone_number=phone,
            username=username_candidate
        )
        # Store provided password hash (user submitted password at signup)
        registration.set_password(password)
        db.session.add(registration)
        db.session.commit()
        # If the current user is an Admin creating a registration via this
        # endpoint, allow immediate creation of the active User (admin flows).
        from flask_login import current_user
        if current_user.is_authenticated and getattr(current_user, 'role', '') == 'Admin':
            # Admin-initiated create: directly create User and mark registration approved
            user = User(username=registration.username)
            user.set_role(User.ROLE_PREVENTION_ADVOCATE)
            user.password_hash = registration.password_hash
            db.session.add(user)
            db.session.flush()
            registration.status = 'Approved'
            registration.reviewed_at = datetime.now(timezone.utc)
            registration.reviewed_by = current_user.user_id
            registration.created_user_id = user.user_id
            db.session.commit()
            flash(f'New Prevention Advocate account for {registration.full_name} created successfully. Username: {user.username}', 'success')
            return redirect(url_for('main.index'))

        # Public signup: leave registration as 'Pending' and notify user
        flash('Your registration has been received and is pending admin approval.', 'info')
        return redirect(url_for('main.index'))

    # Simple form rendering for GET request (test-friendly placeholder)
    # In production this should render a proper template.
    if request.method == 'GET':
        return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute", methods=["POST"], exempt_when=lambda: False)
def login():
    if current_user.is_authenticated:
        # Redirect authenticated users directly to their role dashboard
        role = current_user.role or ''
        if role == 'Admin':
            return redirect(url_for('admin.dashboard'))
        elif role == 'Supervisor':
            return redirect(url_for('supervisor.dashboard'))
        elif role == 'Prevention Advocate':
            return redirect(url_for('champion.dashboard'))
        else:
            # Unknown role - logout and clear session to prevent redirect loop
            from flask import session
            logout_user()
            session.clear()
            flash('Your account has an invalid role. Please contact an administrator.', 'danger')
            # Don't return here - let it fall through to show login form

    if request.method == 'POST':
        # Support both form-based login (HTML) and JSON API login
        if request.is_json:
            payload = request.get_json() or {}
            username = payload.get('username')
            password = payload.get('password')
        else:
            username = request.form.get('username')
            password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user:
            # Check if account is locked
            if user.is_locked():
                locked_until = user.locked_until
                if locked_until and locked_until.tzinfo is None:
                    from datetime import timezone as _tz
                    locked_until = locked_until.replace(tzinfo=_tz.utc)
                remaining_time = int((locked_until - datetime.now(timezone.utc)).total_seconds() / 60)
                if request.is_json:
                    return jsonify({'error': 'Account locked', 'minutes': remaining_time}), 403
                flash(f'Account is locked due to too many failed login attempts. Please try again in {remaining_time} minutes.', 'danger')
                return render_template('auth/login.html')

            # Check password
            if user.check_password(password):
                # Successful login - reset failed attempts
                user.reset_failed_logins()
                login_user(user, remember=True)
                track_login_attempt(success=True)  # Track successful login

                # If JSON request, return access token + set refresh cookie
                if request.is_json:
                    access_ttl = int(os.environ.get('ACCESS_TOKEN_TTL_SECONDS', 900))  # default 15 min
                    refresh_ttl_days = int(os.environ.get('REFRESH_TOKEN_TTL_DAYS', 30))
                    now = datetime.now(timezone.utc)
                    payload_jwt = {
                        'sub': str(user.user_id),
                        'iat': int(now.timestamp()),
                        'exp': int((now + timedelta(seconds=access_ttl)).timestamp()),
                        'role': user.role
                    }
                    token = jwt.encode(payload_jwt, os.environ.get('SECRET_KEY') or current_app.config.get('SECRET_KEY'), algorithm='HS256')

                    # Create refresh token (rotate-able). Store SHA256 hash in DB.
                    raw_refresh = secrets.token_urlsafe(64)
                    refresh_hash = hashlib.sha256(raw_refresh.encode('utf-8')).hexdigest()
                    expires_at = now + timedelta(days=refresh_ttl_days)
                    rt = RefreshToken(user_id=user.user_id, token_hash=refresh_hash, expires_at=expires_at)
                    db.session.add(rt)
                    db.session.commit()

                    response = make_response(jsonify({'access_token': token, 'user': {
                        'user_id': user.user_id,
                        'username': user.username,
                        'email': user.email,
                        'role': user.role,
                        'champion_id': user.champion_id
                    }}))
                    # Set HttpOnly secure cookie for refresh token. SameSite=None for cross-site usage.
                    secure_flag = os.environ.get('FLASK_ENV') == 'production'
                    cookie_domain = current_app.config.get('SESSION_COOKIE_DOMAIN')
                    host = request.host.split(':')[0] if request.host else ''
                    use_domain = None
                    if cookie_domain:
                        norm = cookie_domain[1:] if cookie_domain.startswith('.') else cookie_domain
                        if host == norm or host.endswith('.' + norm):
                            use_domain = cookie_domain
                    if use_domain:
                        response.set_cookie('refresh_token', raw_refresh, httponly=True, secure=secure_flag, samesite='None', path='/', max_age=refresh_ttl_days*24*3600, domain=use_domain)
                    else:
                        response.set_cookie('refresh_token', raw_refresh, httponly=True, secure=secure_flag, samesite='None', path='/', max_age=refresh_ttl_days*24*3600)
                    return response

                # Else form login: flash and redirect as before
                flash('Logged in successfully', 'success')
                role = user.role or ''
                if role == 'Admin':
                    return redirect(url_for('admin.dashboard'))
                elif role == 'Supervisor':
                    return redirect(url_for('supervisor.dashboard'))
                elif role == 'Prevention Advocate':
                    return redirect(url_for('champion.dashboard'))
                else:
                    return redirect(url_for('auth.login'))
            else:
                # Failed login - record attempt
                user.record_failed_login()
                track_login_attempt(success=False)  # Track failed login
                remaining_attempts = 7 - (user.failed_login_attempts or 0)
                if request.is_json:
                    return jsonify({'error': 'Invalid credentials', 'remaining_attempts': remaining_attempts}), 401
                if remaining_attempts > 0:
                    flash(f'Invalid username or password. {remaining_attempts} attempts remaining before account lockout.', 'danger')
                else:
                    flash('Account locked due to too many failed login attempts. Please try again in 30 minutes.', 'danger')
        else:
            # Username not found - don't reveal this info
            track_login_attempt(success=False)  # Track failed login
            if request.is_json:
                return jsonify({'error': 'Invalid credentials'}), 401
            flash('Invalid username or password', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()  # Clear session FIRST
    logout_user()  # Then logout
    flash('You have been logged out.', 'success')
    response = redirect(url_for('auth.login'))
    # Prevent caching of authenticated pages
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    # Force cookie deletion
    cookie_domain = current_app.config.get('SESSION_COOKIE_DOMAIN')
    host = request.host.split(':')[0] if request.host else ''
    use_domain = None
    if cookie_domain:
        norm = cookie_domain[1:] if cookie_domain.startswith('.') else cookie_domain
        if host == norm or host.endswith('.' + norm):
            use_domain = cookie_domain
    if use_domain:
        response.set_cookie('session', '', expires=0, domain=use_domain)
        # Also clear refresh token cookie if present
        response.set_cookie('refresh_token', '', expires=0, path='/', domain=use_domain)
    else:
        response.set_cookie('session', '', expires=0)
        response.set_cookie('refresh_token', '', expires=0, path='/')
    return response
    return response



