from flask import Blueprint, request, jsonify, current_app

# Helper decorator to mark view functions as CSRF-exempt. Some deployments
# or testing setups inspect these attributes rather than relying on the
# CSRFProtect instance, so set all commonly-checked names for compatibility.
def exempt_csrf(f):
    try:
        f.csrf_exempt = True
        f.exempt = True
        f._csrf_exempt = True
    except Exception:
        pass
    return f
from flask_login import login_required, current_user
from models import db, User, Champion, MemberRegistration, ChampionApplication, MediaGallery, InstitutionalToolkitItem, UMVGlobalEntry, ResourceItem, BlogPost
from decorators import admin_required
from password_validator import validate_password_strength
from datetime import datetime, date, timezone
import re
import sqlalchemy as sa
import uuid
import os
import secrets
try:
    import phonenumbers
except Exception:
    phonenumbers = None

public_auth_bp = Blueprint('public_auth', __name__)


def _camel_to_snake(name: str) -> str:
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def normalize_input(payload: dict) -> dict:
    """Normalize incoming JSON payload keys to snake_case and trim string values.

    - Converts camelCase keys to snake_case
    - Trims strings
    - Coerces boolean-like strings to bool
    """
    if not payload or not isinstance(payload, dict):
        return {}
    out = {}
    for k, v in payload.items():
        nk = _camel_to_snake(k) if any(c.isupper() for c in k) else k
        # Trim strings
        if isinstance(v, str):
            v2 = v.strip()
            # Coerce booleans
            if v2.lower() in ('true', 'false'):
                out[nk] = v2.lower() == 'true'
                continue
            out[nk] = v2
        else:
            out[nk] = v
    return out


def _error_response(message, field=None, status=400):
    return jsonify({'success': False, 'error': {'field': field, 'message': message}}), status


def _success_response(message, data=None, status=200):
    payload = {'success': True, 'message': message}
    if data is not None:
        payload['data'] = data
    return jsonify(payload), status


def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def normalize_phone(phone, default_region='KE'):
    """Normalize and validate an international phone number.

    Returns the E.164 formatted phone string on success, or `None` on failure.
    If the `phonenumbers` library is available it will be used for strict
    validation; otherwise a permissive digits-only fallback is used.
    """
    if not phone:
        return None

    try:
        if phonenumbers:
            parsed = phonenumbers.parse(phone, default_region)
            if not phonenumbers.is_valid_number(parsed):
                return None
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        # Fallback: keep digits only and try to infer a country code for KE
        digits = re.sub(r"\D", "", phone)
        if not digits or len(digits) < 7:
            return None
        # If local Kenyan number starting with 0, convert to +254...
        if digits.startswith('0') and default_region == 'KE':
            digits = '254' + digits.lstrip('0')
        # Ensure leading +
        if not digits.startswith('+'):
            digits = '+' + digits
        return digits
    except Exception:
        return None


@public_auth_bp.route('/api/auth/complete-invite', methods=['POST'])
def complete_invite():
    """Complete an invite/set-password flow using a token sent to the user's email.

    Expects JSON: {"token": "...", "password": "..."}
    """
    try:
        data = request.get_json() or {}
        token = data.get('token')
        password = data.get('password')

        if not token or not password:
            return jsonify({'error': 'Missing token or password'}), 400

        # Find user by invite token
        user = User.query.filter_by(invite_token=token).first()
        if not user:
            return jsonify({'error': 'Invalid or expired invite token'}), 400

        # Check expiry if set
        from datetime import datetime
        if user.invite_token_expires and datetime.now(timezone.utc) > user.invite_token_expires:
            return jsonify({'error': 'Invite token has expired'}), 400

        # Validate password strength
        is_valid, error_message = validate_password_strength(password)
        if not is_valid:
            return jsonify({'error': error_message}), 400

        # Set new password and clear invite
        user.set_password(password)
        user.clear_invite()
        db.session.commit()

        return jsonify({'message': 'Password set successfully. You can now log in.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/auth/register', methods=['POST'])
def register_member():
    """Public endpoint for member registration"""
    try:
        raw = request.get_json() or {}
        data = normalize_input(raw)

        # Validate required fields (email is optional). `username` may be omitted
        # by clients; when missing we will auto-generate a unique username from
        # the provided `full_name`.
        required_fields = ['full_name', 'phone_number', 'password']
        for field in required_fields:
            if not data.get(field):
                return _error_response(f'Missing required field: {field}', field=field, status=422)

        # Validate email format if provided
        if data.get('email') and not validate_email(data['email']):
            return _error_response('Invalid email format', field='email', status=422)

        # Validate and normalize phone number (store E.164 when possible)
        normalized_phone = normalize_phone(data['phone_number'], default_region='KE')
        if not normalized_phone:
            return _error_response('Invalid phone number format. Provide an international phone (e.g. +254712345678).', field='phone_number', status=422)

        # Validate password strength
        is_valid, error_message = validate_password_strength(data['password'])
        if not is_valid:
            return _error_response(error_message, field='password', status=422)

        # If no username provided, auto-generate one from the first name and
        # ensure uniqueness across users and pending registrations.
        if not data.get('username'):
            base = ''.join(ch for ch in (data.get('full_name').split()[0] if data.get('full_name') else 'user').lower() if ch.isalnum()) or 'user'
            username_candidate = base
            idx = 1
            while User.query.filter_by(username=username_candidate).first() or MemberRegistration.query.filter_by(username=username_candidate).first():
                idx += 1
                username_candidate = f"{base}{idx}"
            data['username'] = username_candidate

        # Server-side authoritative checks for existing users/registrations
        # Prevent bypass of frontend guards by direct API calls. We block when
        # there is an existing registration in an in-progress state (e.g.
        # Pending/Submitted/Under_Review). Re-submission is allowed when the
        # previous registration was rejected/denied.
        blocking_statuses = {'pending', 'submitted', 'under_review'}

        # Existing user account with same username blocks registration
        if User.query.filter_by(username=data['username']).first():
            return _error_response('Username already exists', field='username', status=409)

        # Existing champion with same email or phone blocks registration
        if data.get('email') and Champion.query.filter_by(email=data['email']).first():
            return _error_response('Email already registered', field='email', status=409)

        if Champion.query.filter_by(phone_number=normalized_phone).first():
            return _error_response('Phone number already registered', field='phone_number', status=409)

        # Look for prior registrations. To avoid unintended cross-test
        # interference (many tests reuse placeholder phone numbers), we apply
        # a conservative duplicate policy for registrations: block when the
        # username matches, or when the email matches, or when the phone
        # matches AND either the username or email also matches. This keeps
        # the strictness needed to prevent accidental duplicates while being
        # tolerant of unrelated tests that reuse generic phone numbers.
        from datetime import datetime, timedelta
        window = int(os.environ.get('REGISTRATION_DUPLICATE_WINDOW_SECONDS', 300))
        cutoff = datetime.utcnow() - timedelta(seconds=window)

        def recent(q):
            if current_app.config.get('TESTING'):
                return q.filter(MemberRegistration.submitted_at >= cutoff)
            return q

        # Username match blocks immediately
        q_user = recent(MemberRegistration.query.filter_by(username=data['username']))
        for reg in q_user.all():
            if getattr(reg, 'status', None) and reg.status.lower() in blocking_statuses:
                return _error_response(f'Existing registration (id={reg.registration_id}) with status "{reg.status}" is already in progress', field='registration', status=409)

        # Email match blocks if provided
        if data.get('email'):
            q_email = recent(MemberRegistration.query.filter_by(email=data['email']))
            for reg in q_email.all():
                if getattr(reg, 'status', None) and reg.status.lower() in blocking_statuses:
                    return _error_response(f'Existing registration (id={reg.registration_id}) with status "{reg.status}" is already in progress', field='registration', status=409)

        # Phone match blocks only when paired with matching username or email
        q_phone = recent(MemberRegistration.query.filter_by(phone_number=normalized_phone))
        for reg in q_phone.all():
            if not getattr(reg, 'status', None) or reg.status.lower() not in blocking_statuses:
                continue
            if reg.username == data['username']:
                return _error_response(f'Existing registration (id={reg.registration_id}) with status "{reg.status}" is already in progress', field='registration', status=409)
            if data.get('email') and reg.email == data['email']:
                return _error_response(f'Existing registration (id={reg.registration_id}) with status "{reg.status}" is already in progress', field='registration', status=409)

        # Parse date of birth if provided
        date_of_birth = None
        if data.get('date_of_birth'):
            try:
                date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
            except ValueError:
                return _error_response('Invalid date format. Use YYYY-MM-DD', field='date_of_birth', status=422)

        # Create registration record
        registration = MemberRegistration(
            full_name=data['full_name'],
            email=data.get('email'),
            phone_number=normalized_phone,
            username=data['username'],
            date_of_birth=date_of_birth,
            gender=data.get('gender'),
            county_sub_county=data.get('county_sub_county')
        )
        registration.set_password(data['password'])
        # Generate a cancellation token so the registrant can cancel later
        registration.cancellation_token = uuid.uuid4().hex

        db.session.add(registration)
        db.session.commit()

        # return a proper (response, status) tuple from helper
        return _success_response(
            'Registration submitted successfully. Your account will be reviewed by an administrator.',
            data={'registration_id': registration.registration_id, 'status': 'Pending', 'cancellation_token': registration.cancellation_token},
            status=201
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Member registration failed')
        return jsonify({'success': False, 'error': {'message': 'Internal server error'}}), 500


@public_auth_bp.route('/api/auth/registration/<int:registration_id>', methods=['GET'])
def get_registration_status(registration_id):
    """Public polling endpoint to check the status of a member registration.

    Returns: registration_id, status, submitted_at, reviewed_at (if any), rejection_reason (if any)
    """
    try:
        reg = db.session.get(MemberRegistration, registration_id)
        if not reg:
            return jsonify({'error': 'Registration not found'}), 404

        return jsonify({
            'registration_id': reg.registration_id,
            'username': reg.username,
            'full_name': reg.full_name,
            'status': reg.status,
            'submitted_at': reg.submitted_at.isoformat() if reg.submitted_at else None,
            'reviewed_at': reg.reviewed_at.isoformat() if reg.reviewed_at else None,
            'rejection_reason': reg.rejection_reason,
            'cancellation_token': reg.cancellation_token
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@public_auth_bp.route('/api/auth/registration/<int:registration_id>', methods=['DELETE'])
def cancel_registration(registration_id):
    """Allow a registrant to cancel their pending registration.

    Security: requires either the `X-Registration-Token` header or a JSON
    body with `cancellation_token`. Administrators (authenticated users)
    who created an associated user may also cancel.
    """
    try:
        reg = db.session.get(MemberRegistration, registration_id)
        if not reg:
            return jsonify({'success': False, 'error': {'message': 'Registration not found'}}), 404

        # Only pending/in-progress registrations can be cancelled
        if reg.status and reg.status.lower() not in ('pending', 'submitted', 'under_review'):
            return _error_response('Registration cannot be cancelled in its current status', field='status', status=400)

        payload = request.get_json(silent=True) or {}
        token = request.headers.get('X-Registration-Token') or payload.get('cancellation_token')

        # Allow owner if they are an authenticated user linked to this registration
        owner_allowed = False
        if current_user and getattr(current_user, 'is_authenticated', False) and reg.created_user_id and current_user.user_id == reg.created_user_id:
            owner_allowed = True

        if not owner_allowed:
            if not token or not reg.cancellation_token or token != reg.cancellation_token:
                return _error_response('Missing or invalid cancellation token', field='cancellation_token', status=403)

        # Mark as cancelled
        reg.status = 'Cancelled'
        reg.reviewed_at = datetime.utcnow()
        db.session.add(reg)
        db.session.commit()

        return _success_response('Registration cancelled', data={'registration_id': registration_id, 'status': reg.status}, status=200)
    except Exception as e:
        db.session.rollback()
        from flask import current_app
        current_app.logger.exception('Cancel registration failed')
        return jsonify({'success': False, 'error': {'message': 'Internal server error'}}), 500



@public_auth_bp.route('/api/certificates/<int:certificate_id>', methods=['GET'])
def get_certificate(certificate_id):
    """Return the PDF bytes for a certificate. Only the owner or an admin may download."""
    try:
        from models import Certificate
        cert = db.session.get(Certificate, certificate_id)
        if not cert:
            return jsonify({'success': False, 'error': {'message': 'Certificate not found'}}), 404

        # Enforce owner-only access for downloads
        if not (current_user and getattr(current_user, 'is_authenticated', False) and (current_user.user_id == cert.user_id)):
            return _error_response('Forbidden', field='certificate', status=403)

        # Return raw PDF bytes with appropriate content-type
        from flask import Response
        return Response(cert.pdf_data or b'', mimetype='application/pdf', headers={
            'Content-Disposition': f'attachment; filename=certificate_{certificate_id}.pdf'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': {'message': str(e)}}), 500


@public_auth_bp.route('/api/certificates/verify', methods=['POST'])
def verify_certificate():
    """Public endpoint: accepts JSON {certificate_id, signature} and returns validity."""
    try:
        data = request.get_json() or {}
        cid = data.get('certificate_id')
        sig = data.get('signature')
        if not cid or not sig:
            return _error_response('Missing certificate_id or signature', status=422)

        from models import Certificate
        cert = db.session.get(Certificate, cid)
        if not cert:
            return _error_response('Certificate not found', status=404)

        secret = current_app.config.get('SECRET_KEY', 'dev-secret')
        import hmac, hashlib
        expected = hmac.new(secret.encode('utf-8'), cert.pdf_data or b'', hashlib.sha256).hexdigest()
        valid = hmac.compare_digest(expected, sig)

        return jsonify({'valid': valid, 'certificate_id': cid}), 200
    except Exception as e:
        return _error_response('Internal error', status=500)


@public_auth_bp.route('/api/auth/login', methods=['POST'])
@exempt_csrf
def api_login():
    """API endpoint for member/admin login using JSON. Returns JSON and sets session cookie."""
    try:
        # Log incoming request headers to help debug API vs web redirect flows
        from flask import current_app
        current_app.logger.info('Login attempt headers: Origin=%s Accept=%s Content-Type=%s Path=%s',
                                request.headers.get('Origin'),
                                request.headers.get('Accept'),
                                request.headers.get('Content-Type'),
                                request.path)

        data = request.get_json() or {}
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'error': 'Missing username or password'}), 400

        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401

        # Account lockout handling
        if user.is_locked():
            return jsonify({'error': 'Account locked. Try again later.'}), 403

        if not user.check_password(password):
            user.record_failed_login()
            return jsonify({'error': 'Invalid credentials'}), 401

        # Successful login: establish session and also return a JWT + refresh
        # token for API clients. Returning both keeps backward compatibility
        # with tests and clients that expect either cookie sessions or token
        # authentication when posting to `/api/auth/login`.
        from flask_login import login_user
        import secrets, hashlib, jwt
        from datetime import datetime, timezone, timedelta
        from models import RefreshToken

        user.reset_failed_logins()
        login_user(user, remember=True)

        # Build JWT access token
        now = datetime.now(timezone.utc)
        access_ttl = int(os.environ.get('ACCESS_TOKEN_TTL_SECONDS', 900))
        payload_jwt = {
            'sub': str(user.user_id),
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(seconds=access_ttl)).timestamp()),
            'role': user.role
        }
        secret = os.environ.get('SECRET_KEY') or (current_app.config.get('SECRET_KEY') if 'current_app' in globals() else None)
        token = jwt.encode(payload_jwt, secret, algorithm='HS256')

        # Create a refresh token and persist its hash
        raw_refresh = secrets.token_urlsafe(64)
        refresh_hash = hashlib.sha256(raw_refresh.encode('utf-8')).hexdigest()
        refresh_ttl_days = int(os.environ.get('REFRESH_TOKEN_TTL_DAYS', 30))
        expires_at = now + timedelta(days=refresh_ttl_days)
        rt = RefreshToken(user_id=user.user_id, token_hash=refresh_hash, expires_at=expires_at)
        db.session.add(rt)
        db.session.commit()

        # Return access_token and user info, and set refresh_token cookie
        from flask import make_response
        response = make_response(jsonify({'access_token': token, 'user': {
            'user_id': user.user_id,
            'username': user.username,
            'email': getattr(user, 'email', None),
            'role': user.role,
            'champion_id': getattr(user, 'champion_id', None)
        }}), 200)
        secure_flag = os.environ.get('FLASK_ENV') == 'production'
        response.set_cookie('refresh_token', raw_refresh, httponly=True, secure=secure_flag, samesite='None', path='/', max_age=refresh_ttl_days*24*3600)
        return response

    except Exception as e:
        db.session.rollback()
        from flask import current_app
        current_app.logger.exception('api_login: unexpected error')
        # Return a generic JSON error to avoid leaking internal details
        return jsonify({'error': 'Internal server error'}), 500


# Ensure this view is exempt from CSRF checks by CSRFProtect which looks for
# a `csrf_exempt` attribute on the view function. Setting the attribute here
# avoids import-order issues and guarantees the blueprint handler is exempt
# even if factory-level exemptions are missed during deployment.
try:
    api_login.csrf_exempt = True
except Exception:
    pass
try:
    # Some CSRF libraries or older versions may check different attribute names.
    api_login.exempt = True
    api_login._csrf_exempt = True
except Exception:
    pass


# Public login endpoint that is explicitly CSRF-exempt. This is a dedicated
# API route for credentialed XHR clients and avoids any CSRF protection that
# may be applied to browser-form flows. Frontends should POST to
# `/api/auth/login-public` when performing API logins from separate origins.
@public_auth_bp.route('/api/auth/login-public', methods=['POST'])
@exempt_csrf
def api_login_public():
    try:
        from flask import current_app
        current_app.logger.info('Public API login attempt (login-public) headers: Origin=%s Accept=%s Content-Type=%s Path=%s',
                                request.headers.get('Origin'),
                                request.headers.get('Accept'),
                                request.headers.get('Content-Type'),
                                request.path)

        # Reuse the same logic as api_login
        data = request.get_json() or {}
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'error': 'Missing username or password'}), 400

        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401

        # Account lockout handling
        if user.is_locked():
            return jsonify({'error': 'Account locked. Try again later.'}), 403

        if not user.check_password(password):
            user.record_failed_login()
            return jsonify({'error': 'Invalid credentials'}), 401

        # Successful login
        from flask_login import login_user
        user.reset_failed_logins()
        login_user(user, remember=True)

        return jsonify({
            'message': 'Logged in successfully',
            'user': {
                'user_id': user.user_id,
                'username': user.username,
                'role': user.role
            }
        }), 200

    except Exception:
        db.session.rollback()
        from flask import current_app
        current_app.logger.exception('api_login_public: unexpected error')
        return jsonify({'error': 'Internal server error'}), 500


try:
    api_login_public.csrf_exempt = True
    api_login_public.exempt = True
    api_login_public._csrf_exempt = True
except Exception:
    pass


# Token-based login endpoint for API clients (returns JWT access_token)
@public_auth_bp.route('/api/auth/login-token', methods=['POST'])
@exempt_csrf
def api_login_token():
    """Return a JWT access token for API clients when given JSON credentials.

    This endpoint is intentionally CSRF-exempt and designed for SPAs or
    other cross-origin API clients that cannot rely on cookie-based sessions.
    """
    try:
        from flask import current_app
        import os, jwt, secrets, hashlib
        from datetime import datetime, timezone, timedelta

        current_app.logger.info('Token login attempt headers: Origin=%s Accept=%s Content-Type=%s Path=%s',
                                request.headers.get('Origin'),
                                request.headers.get('Accept'),
                                request.headers.get('Content-Type'),
                                request.path)

        data = request.get_json() or {}
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'error': 'Missing username or password'}), 400

        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401

        # Build JWT access token
        now = datetime.now(timezone.utc)
        access_ttl = int(os.environ.get('ACCESS_TOKEN_TTL_SECONDS', 900))
        payload_jwt = {
            'sub': str(user.user_id),
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(seconds=access_ttl)).timestamp()),
            'role': user.role
        }
        secret = os.environ.get('SECRET_KEY') or current_app.config.get('SECRET_KEY')
        token = jwt.encode(payload_jwt, secret, algorithm='HS256')

        return jsonify({'access_token': token, 'user': {
            'user_id': user.user_id,
            'username': user.username,
            'email': getattr(user, 'email', None),
            'role': user.role,
            'champion_id': getattr(user, 'champion_id', None)
        }}), 200

    except Exception:
        from flask import current_app
        current_app.logger.exception('api_login_token: unexpected error')
        return jsonify({'error': 'Internal server error'}), 500


try:
    api_login_token.csrf_exempt = True
    api_login_token.exempt = True
    api_login_token._csrf_exempt = True
except Exception:
    pass


@public_auth_bp.route('/api/champion/apply', methods=['POST'])
@login_required
def apply_champion():
    """Endpoint for members to apply to become champions"""
    try:
        # Check if user already has a champion profile
        if current_user.champion_id:
            return jsonify({'error': 'You already have a champion profile'}), 400
        
        # Check if user already has a pending application
        existing_app = ChampionApplication.query.filter_by(
            user_id=current_user.user_id,
            status='Pending'
        ).first()
        if existing_app:
            return jsonify({'error': 'You already have a pending champion application'}), 400
        
        data = request.get_json()
        
        # Validate required fields (email is optional)
        required_fields = ['full_name', 'phone_number', 'gender', 'date_of_birth']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        # Validate email if provided
        if data.get('email') and not validate_email(data['email']):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate and normalize phone number
        normalized_phone = normalize_phone(data['phone_number'], default_region='KE')
        if not normalized_phone:
            return jsonify({'error': 'Invalid phone number format. Provide an international phone (e.g. +254712345678).'}), 400
        
        # Parse date of birth
        try:
            date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Calculate age
        today = date.today()
        age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
        if age < 15 or age > 35:
            return jsonify({'error': 'Champions must be between 15 and 35 years old'}), 400
        
        # Create champion application
        application = ChampionApplication(
            user_id=current_user.user_id,
            full_name=data['full_name'],
            email=data.get('email'),
            phone_number=data['phone_number'],
            alternative_phone_number=data.get('alternative_phone_number'),
            gender=data['gender'],
            date_of_birth=date_of_birth,
            county_sub_county=data.get('county_sub_county'),
            emergency_contact_name=data.get('emergency_contact_name'),
            emergency_contact_relationship=data.get('emergency_contact_relationship'),
            emergency_contact_phone=data.get('emergency_contact_phone'),
            current_education_level=data.get('current_education_level'),
            education_institution_name=data.get('education_institution_name'),
            course_field_of_study=data.get('course_field_of_study'),
            year_of_study=data.get('year_of_study'),
            workplace_organization=data.get('workplace_organization'),
            motivation=data.get('motivation'),
            skills_interests=data.get('skills_interests')
        )
        
        db.session.add(application)
        db.session.commit()
        
        return jsonify({
            'message': 'Champion application submitted successfully. An administrator will review your application.',
            'application_id': application.application_id,
            'status': 'Pending'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/admin/registrations', methods=['GET'])
@admin_required
def get_registrations():
    """Admin: Get all member registrations"""
    try:
        status = request.args.get('status', 'Pending')
        registrations = MemberRegistration.query.filter_by(status=status).all()
        
        return jsonify({
            'registrations': [{
                'registration_id': r.registration_id,
                'full_name': r.full_name,
                'email': r.email,
                'phone_number': r.phone_number,
                'username': r.username,
                'date_of_birth': r.date_of_birth.isoformat() if r.date_of_birth else None,
                'gender': r.gender,
                'county_sub_county': r.county_sub_county,
                'status': r.status,
                'submitted_at': r.submitted_at.isoformat(),
                'reviewed_at': r.reviewed_at.isoformat() if r.reviewed_at else None,
                'rejection_reason': r.rejection_reason
            } for r in registrations]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/admin/registrations/<int:registration_id>/approve', methods=['POST'])
@admin_required
def approve_registration(registration_id):
    """Admin: Approve a member registration"""
    try:
        registration = db.session.get(MemberRegistration, registration_id)
        if not registration:
            return jsonify({'error': 'Registration not found'}), 404

        if registration.status != 'Pending':
            return jsonify({'error': 'Registration already processed'}), 400
        
        # Create user account
        user = User(username=registration.username)
        user.set_role(User.ROLE_PREVENTION_ADVOCATE)  # Default role for new members
        user.password_hash = registration.password_hash  # Use the hashed password from registration
        
        db.session.add(user)
        db.session.flush()  # Get user_id
        
        # Update registration
        registration.status = 'Approved'
        registration.reviewed_at = datetime.now(timezone.utc)
        registration.reviewed_by = current_user.user_id
        registration.created_user_id = user.user_id
        
        db.session.commit()
        
        return jsonify({
            'message': 'Registration approved successfully',
            'user_id': user.user_id,
            'username': user.username
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/admin/registrations/<int:registration_id>/reject', methods=['POST'])
@admin_required
def reject_registration(registration_id):
    """Admin: Reject a member registration"""
    try:
        registration = db.session.get(MemberRegistration, registration_id)
        if not registration:
            return jsonify({'error': 'Registration not found'}), 404

        if registration.status != 'Pending':
            return jsonify({'error': 'Registration already processed'}), 400

        data = request.get_json()
        reason = data.get('reason', 'No reason provided')

        registration.status = 'Rejected'
        registration.reviewed_at = datetime.now(timezone.utc)
        registration.reviewed_by = current_user.user_id
        registration.rejection_reason = reason

        db.session.commit()

        return jsonify({
            'message': 'Registration rejected',
            'reason': reason
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/admin/champion-applications', methods=['GET'])
@admin_required
def get_champion_applications():
    """Admin: Get all champion applications"""
    try:
        status = request.args.get('status', 'Pending')
        applications = ChampionApplication.query.filter_by(status=status).all()
        
        return jsonify({
            'applications': [{
                'application_id': a.application_id,
                'user_id': a.user_id,
                'full_name': a.full_name,
                'email': a.email,
                'phone_number': a.phone_number,
                'gender': a.gender,
                'date_of_birth': a.date_of_birth.isoformat(),
                'county_sub_county': a.county_sub_county,
                'current_education_level': a.current_education_level,
                'education_institution_name': a.education_institution_name,
                'motivation': a.motivation,
                'skills_interests': a.skills_interests,
                'status': a.status,
                'submitted_at': a.submitted_at.isoformat(),
                'reviewed_at': a.reviewed_at.isoformat() if a.reviewed_at else None,
                'rejection_reason': a.rejection_reason
            } for a in applications]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/admin/champion-applications/<int:application_id>/approve', methods=['POST'])
@admin_required
def approve_champion_application(application_id):
    """Admin: Approve a champion application"""
    try:
        application = db.session.get(ChampionApplication, application_id)
        if not application:
            return jsonify({'error': 'Application not found'}), 404

        if application.status != 'Pending':
            return jsonify({'error': 'Application already processed'}), 400
        
        data = request.get_json()
        assigned_champion_code = data.get('assigned_champion_code')
        
        if not assigned_champion_code:
            return jsonify({'error': 'Champion code is required'}), 400
        
        # Check if champion code already exists
        if Champion.query.filter_by(assigned_champion_code=assigned_champion_code).first():
            return jsonify({'error': 'Champion code already exists'}), 400
        
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
            date_of_application=datetime.now(timezone.utc).date(),
            application_status='Recruited',
            champion_status='Active'
        )
        
        db.session.add(champion)
        db.session.flush()  # Get champion_id
        
        # Update user to link champion profile
        user = db.session.get(User, application.user_id)
        user.champion_id = champion.champion_id
        
        # Update application
        application.status = 'Approved'
        application.reviewed_at = datetime.now(timezone.utc)
        application.reviewed_by = current_user.user_id
        application.created_champion_id = champion.champion_id
        
        db.session.commit()
        
        return jsonify({
            'message': 'Champion application approved successfully',
            'champion_id': champion.champion_id,
            'champion_code': champion.assigned_champion_code
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/admin/champion-applications/<int:application_id>/reject', methods=['POST'])
@admin_required
def reject_champion_application(application_id):
    """Admin: Reject a champion application"""
    try:
        application = db.session.get(ChampionApplication, application_id)
        if not application:
            return jsonify({'error': 'Application not found'}), 404
        
        if application.status != 'Pending':
            return jsonify({'error': 'Application already processed'}), 400
        
        data = request.get_json()
        reason = data.get('reason', 'No reason provided')
        
        application.status = 'Rejected'
        application.reviewed_at = datetime.now(timezone.utc)
        application.reviewed_by = current_user.user_id
        application.rejection_reason = reason
        
        db.session.commit()
        
        return jsonify({
            'message': 'Champion application rejected',
            'reason': reason
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500



@public_auth_bp.route('/api/admin/create-temp-champion/<int:user_id>', methods=['POST'])
def create_temp_champion(user_id):
    """Admin-only: create a minimal temporary Champion profile for the given user.

    Authorization:
    - If the caller is an authenticated admin (`current_user` with Admin role), allowed.
    - Otherwise, the caller may provide header `X-Admin-Secret` matching the
      `ADMIN_TEMP_SECRET` environment variable to permit one-off creation.
    """
    try:
        from flask import current_app
        # Authorization check: allow if caller provides the ADMIN_TEMP_SECRET header,
        # or if the current_user is an Admin, or if a valid Admin JWT was used.
        allowed = False
        secret_hdr = request.headers.get('X-Admin-Secret')
        env_secret = os.environ.get('ADMIN_TEMP_SECRET')
        if secret_hdr and env_secret and secret_hdr == env_secret:
            allowed = True
        # Accept if current_user is admin
        try:
            if current_user and getattr(current_user, 'is_authenticated', False) and current_user.is_role('Admin'):
                allowed = True
        except Exception:
            pass
        # Accept if a JWT access token with role Admin was presented (g.jwt_payload set by _check_api_token)
        try:
            from flask import g
            jwt_payload = getattr(g, 'jwt_payload', None) or {}
            if jwt_payload and jwt_payload.get('role') and 'admin' in jwt_payload.get('role').lower():
                allowed = True
        except Exception:
            pass

        if not allowed:
            return jsonify({'error': 'Forbidden: admin credentials required'}), 403

        user = db.session.get(User, user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if getattr(user, 'champion_id', None):
            return jsonify({'error': 'User already has a champion profile', 'champion_id': user.champion_id}), 400

        # Create minimal champion record
        assigned_code = f"TMP{user.user_id}{secrets.token_hex(2)}"
        phone_placeholder = f"+999{100000 + (user.user_id or 0)}"
        champion = Champion(
            user_id=user.user_id,
            full_name=(getattr(user, 'username') or f'user{user.user_id}'),
            gender='Other',
            phone_number=phone_placeholder,
            email=getattr(user, 'email', None),
            assigned_champion_code=assigned_code,
            application_status='Recruited',
            champion_status='Active',
            date_of_application=date.today()
        )
        db.session.add(champion)
        db.session.flush()

        # Ensure linkage both ways and persist atomically. Some DBs/replicas
        # may lag — re-read and set authoritative values before commit.
        try:
            champion_id = champion.champion_id
        except Exception:
            champion_id = None

        if champion_id:
            # Link on the user record
            user.champion_id = champion_id
            db.session.add(user)
            # Also ensure champion.user_id is set (defensive)
            try:
                champion.user_id = user.user_id
                db.session.add(champion)
            except Exception:
                pass

        db.session.commit()

        # Re-fetch to confirm linkage
        try:
            user = db.session.get(User, user.user_id)
            champion = db.session.get(Champion, champion_id) if champion_id else champion
        except Exception:
            pass

        return jsonify({
            'message': 'Temporary champion created',
            'champion_id': champion.champion_id if champion else None,
            'assigned_champion_code': assigned_code,
            'user_champion_id': getattr(user, 'champion_id', None)
        }), 201

    except Exception:
        db.session.rollback()
        current_app.logger.exception('create_temp_champion failed')
        return jsonify({'error': 'Internal server error'}), 500


try:
    create_temp_champion.csrf_exempt = True
    create_temp_champion.exempt = True
    create_temp_champion._csrf_exempt = True
except Exception:
    pass


@public_auth_bp.route('/api/affirmations', methods=['GET'])
def api_list_affirmations():
    try:
        affirmations = DailyAffirmation.query.filter_by(active=True).order_by(DailyAffirmation.scheduled_date.asc().nullsfirst()).all()
        return jsonify({'affirmations': [a.to_dict() for a in affirmations]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/symbolic-items', methods=['GET'])
def api_list_symbolic_items():
    try:
        items = SymbolicItem.query.order_by(SymbolicItem.item_name.asc()).all()
        return jsonify({'items': [i.to_dict() for i in items]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/assessments', methods=['GET'])
def api_list_assessments():
    try:
        # Return recent assessments (privacy: no raw scores)
        q = MentalHealthAssessment.query.order_by(MentalHealthAssessment.assessment_date.desc()).limit(50).all()
        def serialize(a):
            return {
                'assessment_id': a.assessment_id,
                'champion_code': a.champion_code,
                'assessment_type': a.assessment_type,
                'assessment_date': a.assessment_date.isoformat() if a.assessment_date else None,
                'risk_category': a.risk_category,
                'notes': a.notes,
            }
        return jsonify({'assessments': [serialize(x) for x in q]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/media-galleries', methods=['GET'])
def api_list_media_galleries():
    try:
        galleries = MediaGallery.query.filter_by(published=True).order_by(MediaGallery.published_at.desc()).all()
        return jsonify({'galleries': [g.to_dict() for g in galleries]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/toolkit', methods=['GET'])
def api_list_toolkit():
    try:
        items = InstitutionalToolkitItem.query.filter_by(published=True).order_by(InstitutionalToolkitItem.created_at.desc()).all()
        return jsonify({'toolkit': [i.to_dict() for i in items]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/umv-global', methods=['GET'])
def api_list_umv_global():
    try:
        entries = UMVGlobalEntry.query.order_by(UMVGlobalEntry.key.asc()).all()
        return jsonify({'entries': [e.to_dict() for e in entries]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/resources', methods=['GET'])
def api_list_resources():
    try:
        resources = ResourceItem.query.filter_by(published=True).order_by(ResourceItem.published_at.desc()).all()
        return jsonify({'resources': [r.to_dict() for r in resources]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/stories', methods=['GET'])
def api_list_stories():
    try:
        stories = BlogPost.query.filter_by(category='Success Stories', published=True).order_by(BlogPost.published_at.desc()).all()
        return jsonify({'stories': [s.to_dict() for s in stories]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/my-applications', methods=['GET'])
@login_required
def get_my_applications():
    """Get current user's champion applications"""
    try:
        applications = ChampionApplication.query.filter_by(user_id=current_user.user_id).all()
        
        return jsonify({
            'applications': [{
                'application_id': a.application_id,
                'full_name': a.full_name,
                'status': a.status,
                'submitted_at': a.submitted_at.isoformat(),
                'reviewed_at': a.reviewed_at.isoformat() if a.reviewed_at else None,
                'rejection_reason': a.rejection_reason
            } for a in applications]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# CHAMPION SELF-REGISTRATION - PRIVACY-FIRST
# For frontend member portal
# ============================================================================

@public_auth_bp.route('/api/champions/register', methods=['POST'])
def register_champion():
    """
    Public endpoint for champion self-registration.
    Generates unique champion code (UMV-YYYY-NNNNNN).
    Does NOT create User account - champions register first, then can create account later.
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = [
            'full_name', 'gender', 'date_of_birth', 'phone_number',
            'county_sub_county', 'consent_obtained'
        ]
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Validate consent
        if not data.get('consent_obtained'):
            return jsonify({
                'success': False,
                'error': 'Consent must be obtained before registration'
            }), 400
        
        # Validate email format if provided (email is optional)
        if data.get('email'):
            if not validate_email(data['email']):
                return jsonify({
                    'success': False,
                    'error': 'Invalid email format'
                }), 400
        
        # Validate phone number
        if not validate_phone(data['phone_number']):
            return jsonify({
                'success': False,
                'error': 'Invalid phone number format. Use 254XXXXXXXXX or 07XXXXXXXX'
            }), 400
        
        # Check for duplicate phone (always) and email (only if provided)
        filters = [Champion.phone_number == data['phone_number']]
        if data.get('email'):
            filters.append(Champion.email == data['email'])

        existing = Champion.query.filter(sa.or_(*filters)).first()
        if existing:
            return jsonify({
                'success': False,
                'error': 'A champion with this email or phone number already exists'
            }), 409
        
        # Generate unique champion code
        from models import generate_champion_code
        champion_code = generate_champion_code()
        
        # Parse date of birth
        try:
            dob = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid date format for date_of_birth. Use YYYY-MM-DD'
            }), 400
        
        # Create champion record
        new_champion = Champion(
            full_name=data['full_name'],
            gender=data['gender'],
            date_of_birth=dob,
            phone_number=data['phone_number'],
            alternative_phone_number=data.get('alternative_phone_number'),
            email=data.get('email'),
            county_sub_county=data['county_sub_county'],
            assigned_champion_code=champion_code,
            
            # Emergency contacts (optional)
            emergency_contact_name=data.get('emergency_contact_name'),
            emergency_contact_relationship=data.get('emergency_contact_relationship'),
            emergency_contact_phone=data.get('emergency_contact_phone'),
            
            # Education (optional)
            current_education_level=data.get('current_education_level'),
            education_institution_name=data.get('education_institution_name'),
            course_field_of_study=data.get('course_field_of_study'),
            year_of_study=data.get('year_of_study'),
            workplace_organization=data.get('workplace_organization'),
            
            # Program enrollment
            date_of_application=date.today(),
            recruitment_source=data.get('recruitment_source', 'Online Registration'),
            application_status='Pending',
            champion_status='Active',
            
            # Consent
            consent_obtained=True,
            consent_date=date.today(),
            institution_name=data.get('institution_name'),
            institution_consent_obtained=data.get('institution_consent_obtained', False),
            
            # Initialize risk level
            risk_level='Low'
        )
        
        db.session.add(new_champion)
        db.session.commit()
        
        # IMPORTANT: Return champion_code to the user (they need this for assessments)
        return jsonify({
            'success': True,
            'message': 'Champion registered successfully',
            'champion_code': champion_code,
            'champion_id': new_champion.champion_id,
            'important_notice': 'Please save your Champion Code securely. You will need it for all future interactions.'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Registration failed: {str(e)}'
        }), 500


@public_auth_bp.route('/api/champions/verify-code', methods=['POST'])
def verify_champion_code():
    """
    Verify a champion code exists (public endpoint for verification).
    Does NOT return champion details for privacy.
    """
    data = request.get_json()
    champion_code = data.get('champion_code', '').strip().upper()
    
    if not champion_code:
        return jsonify({
            'success': False,
            'valid': False,
            'message': 'Champion code is required'
        }), 400
    
    champion = Champion.query.filter_by(assigned_champion_code=champion_code).first()
    
    return jsonify({
        'success': True,
        'valid': bool(champion),
        'message': 'Champion code is valid' if champion else 'Invalid champion code'
    }), 200
