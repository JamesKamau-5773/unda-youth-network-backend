from flask import Blueprint, jsonify, request, g, current_app
from flask import make_response
from models import db, Champion, YouthSupport, User, RefferalPathway, TrainingRecord, Event, BlogPost
from sqlalchemy import func
from datetime import datetime, date, timezone
from flask import request
from flask_login import login_required, current_user
import json


def _snake_to_camel(s: str) -> str:
    parts = s.split('_')
    return parts[0] + ''.join(p.title() for p in parts[1:]) if parts else s


def _camelize_dict(d: dict, keys: list = None) -> dict:
    """Return a shallow copy of d with selected keys converted to camelCase."""
    out = {}
    if keys is None:
        keys = list(d.keys())
    for k in keys:
        v = d.get(k)
        out[_snake_to_camel(k)] = v
    return out

# reuse phone normalization/email validation from public_auth when available
try:
    from blueprints.public_auth import normalize_phone, validate_email
except Exception:
    normalize_phone = None
    def validate_email(e):
        return True

import os
from functools import wraps
import os
import jwt
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from models import RefreshToken


def _check_api_token():
    """Return True if request provides a valid API token via Authorization header."""
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return False
    token = auth.split(' ', 1)[1]
    # First allow a simple smoke token configured in env for legacy scripts
    api_token = os.environ.get('API_SMOKE_TOKEN')
    if api_token and token == api_token:
        return True

    # Otherwise try to validate as JWT access token
    try:
        import jwt
        secret = os.environ.get('SECRET_KEY') or current_app.config.get('SECRET_KEY')
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        # Attach payload to request context for downstream handlers
        g.jwt_payload = payload
        return True
    except Exception:
        return False


def api_auth_optional(f):
    """Decorator allowing either a logged-in user or a bearer token (for automation).

    When a bearer token is used the endpoint must accept `user_id` or `champion_id`
    in the JSON payload to indicate which record to act on.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if current_user and current_user.is_authenticated:
            return f(*args, **kwargs)
        if _check_api_token():
            return f(*args, **kwargs)
        return jsonify({'error': 'Unauthorized'}), 401
    return wrapper

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/auth/login', methods=['POST'])
def api_auth_login():
    if not request.is_json:
        return jsonify({'error': 'Expected application/json'}), 400
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'username and password required'}), 400
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401

    now = datetime.now(timezone.utc)
    access_ttl = int(os.environ.get('ACCESS_TOKEN_TTL_SECONDS', 900))
    refresh_ttl_days = int(os.environ.get('REFRESH_TOKEN_TTL_DAYS', 30))
    payload_jwt = {
        'sub': str(user.user_id),
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(seconds=access_ttl)).timestamp()),
        'role': user.role
    }
    token = jwt.encode(payload_jwt, os.environ.get('SECRET_KEY') or current_app.config.get('SECRET_KEY'), algorithm='HS256')

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
    secure_flag = os.environ.get('FLASK_ENV') == 'production'
    # Only set cookie domain when it actually applies to the current host
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


@api_bp.route('/auth/refresh', methods=['POST'])
def api_auth_refresh():
    raw = request.cookies.get('refresh_token')
    if not raw:
        return jsonify({'error': 'Missing refresh token'}), 401

    hashed = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    rt = RefreshToken.query.filter_by(token_hash=hashed, revoked=False).first()
    if not rt:
        return jsonify({'error': 'Invalid refresh token'}), 401
    if rt.expires_at:
        exp_at = rt.expires_at
        if exp_at.tzinfo is None:
            exp_at = exp_at.replace(tzinfo=timezone.utc)
        if exp_at < datetime.now(timezone.utc):
            return jsonify({'error': 'Refresh token expired'}), 401

    try:
        rt.revoked = True
        db.session.add(rt)

        new_raw = secrets.token_urlsafe(64)
        new_hash = hashlib.sha256(new_raw.encode('utf-8')).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(days=int(os.environ.get('REFRESH_TOKEN_TTL_DAYS', 30)))
        new_rt = RefreshToken(user_id=rt.user_id, token_hash=new_hash, expires_at=expires_at)
        db.session.add(new_rt)
        db.session.commit()

        user = db.session.get(User, rt.user_id)
        now = datetime.now(timezone.utc)
        access_ttl = int(os.environ.get('ACCESS_TOKEN_TTL_SECONDS', 900))
        payload_jwt = {
            'sub': str(user.user_id),
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(seconds=access_ttl)).timestamp()),
            'role': user.role
        }
        token = jwt.encode(payload_jwt, os.environ.get('SECRET_KEY') or current_app.config.get('SECRET_KEY'), algorithm='HS256')

        response = make_response(jsonify({'access_token': token}))
        secure_flag = os.environ.get('FLASK_ENV') == 'production'
        cookie_domain = current_app.config.get('SESSION_COOKIE_DOMAIN')
        host = request.host.split(':')[0] if request.host else ''
        use_domain = None
        if cookie_domain:
            norm = cookie_domain[1:] if cookie_domain.startswith('.') else cookie_domain
            if host == norm or host.endswith('.' + norm):
                use_domain = cookie_domain
        if use_domain:
            response.set_cookie('refresh_token', new_raw, httponly=True, secure=secure_flag, samesite='None', path='/', max_age=int(os.environ.get('REFRESH_TOKEN_TTL_DAYS', 30))*24*3600, domain=use_domain)
        else:
            response.set_cookie('refresh_token', new_raw, httponly=True, secure=secure_flag, samesite='None', path='/', max_age=int(os.environ.get('REFRESH_TOKEN_TTL_DAYS', 30))*24*3600)
        return response
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error rotating refresh token')
        return jsonify({'error': 'Failed to rotate refresh token'}), 500


@api_bp.route('/auth/logout', methods=['POST'])
def api_auth_logout():
    raw = request.cookies.get('refresh_token')
    if raw:
        hashed = hashlib.sha256(raw.encode('utf-8')).hexdigest()
        rt = RefreshToken.query.filter_by(token_hash=hashed).first()
        if rt:
            rt.revoked = True
            try:
                db.session.add(rt)
                db.session.commit()
            except Exception:
                db.session.rollback()
    response = make_response(jsonify({'success': True}))
    cookie_domain = current_app.config.get('SESSION_COOKIE_DOMAIN')
    host = request.host.split(':')[0] if request.host else ''
    use_domain = None
    if cookie_domain:
        norm = cookie_domain[1:] if cookie_domain.startswith('.') else cookie_domain
        if host == norm or host.endswith('.' + norm):
            use_domain = cookie_domain
    if use_domain:
        response.set_cookie('refresh_token', '', expires=0, path='/', domain=use_domain)
        response.set_cookie('session', '', expires=0, path='/', domain=use_domain)
    else:
        response.set_cookie('refresh_token', '', expires=0, path='/')
        response.set_cookie('session', '', expires=0, path='/')
    return response


@api_bp.route('/auth/me', methods=['GET'])
@login_required
def api_auth_me():
    """Return current authenticated user and linked champion profile.

    Fields are returned in camelCase to match typical JS/React clients.
    """
    try:
        user = current_user
        user_data = {
            'user_id': user.user_id,
            'username': user.username,
            'email': getattr(user, 'email', None),
            'role': user.role,
            'champion_id': getattr(user, 'champion_id', None),
            'date_of_birth': user.date_of_birth.isoformat() if getattr(user, 'date_of_birth', None) else None,
            'gender': getattr(user, 'gender', None),
            'county_sub_county': getattr(user, 'county_sub_county', None)
        }

        out = {'user': _camelize_dict(user_data)}

        # If user has a champion profile, include key champion fields
        if getattr(user, 'champion_id', None):
            try:
                champ = Champion.query.filter_by(champion_id=user.champion_id).first()
            except Exception:
                champ = None

            if champ:
                champ_fields = {
                    'champion_id': champ.champion_id,
                    'full_name': champ.full_name,
                    'email': champ.email,
                    'phone_number': champ.phone_number,
                    'alternative_phone_number': champ.alternative_phone_number,
                    'county_sub_county': champ.county_sub_county,
                    'assigned_champion_code': champ.assigned_champion_code,
                    'date_of_birth': champ.date_of_birth.isoformat() if champ.date_of_birth else None,
                    'gender': champ.gender,
                }
                out['champion'] = _camelize_dict(champ_fields)

        return jsonify(out), 200
    except Exception:
        return jsonify({'error': 'Failed to fetch user information'}), 500


@api_bp.route('/auth/me', methods=['PUT'])
@login_required
def api_auth_me_update():
    """Update current authenticated user profile.

    Frontend expects PUT /api/auth/me for profile updates.
    Accepts JSON or multipart/form-data. Normalizes camelCase to snake_case.
    """
    from blueprints.public_auth import normalize_input

    raw = None
    if request.is_json:
        raw = request.get_json() or {}
    else:
        try:
            raw = request.form.to_dict() or {}
        except Exception:
            raw = {}

    data = normalize_input(raw or {})
    user = current_user

    try:
        if 'email' in data and data['email']:
            if not validate_email(data['email']):
                return jsonify({'error': 'Invalid email format'}), 400
            user.email = data['email']

        if 'username' in data and data['username']:
            existing = User.query.filter(User.username == data['username'], User.user_id != user.user_id).first()
            if existing:
                return jsonify({'error': 'Username already taken'}), 409
            user.username = data['username']

        if 'date_of_birth' in data and data['date_of_birth']:
            try:
                user.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
            except Exception:
                pass

        if 'gender' in data and data['gender']:
            user.gender = data['gender']

        if 'county_sub_county' in data and data['county_sub_county']:
            user.county_sub_county = data['county_sub_county']

        # Update linked champion profile if exists
        champion = None
        if user.champion_id:
            champion = db.session.get(Champion, user.champion_id)

        if champion:
            if 'full_name' in data and data['full_name']:
                champion.full_name = data['full_name']
            if 'date_of_birth' in data and data['date_of_birth']:
                try:
                    champion.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
                except Exception:
                    return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
            if 'phone_number' in data and data['phone_number']:
                if normalize_phone:
                    normalized = normalize_phone(data['phone_number'])
                    if not normalized:
                        return jsonify({'error': 'Invalid phone number'}), 400
                    champion.phone_number = normalized
                else:
                    champion.phone_number = data['phone_number']
            if 'county_sub_county' in data and data['county_sub_county']:
                champion.county_sub_county = data['county_sub_county']

        db.session.add(user)
        if champion:
            db.session.add(champion)
        db.session.commit()

        # Return updated profile in camelCase
        user_data = {
            'user_id': user.user_id,
            'username': user.username,
            'email': getattr(user, 'email', None),
            'role': user.role,
            'champion_id': getattr(user, 'champion_id', None),
            'date_of_birth': user.date_of_birth.isoformat() if getattr(user, 'date_of_birth', None) else None,
            'gender': getattr(user, 'gender', None),
            'county_sub_county': getattr(user, 'county_sub_county', None)
        }

        out = {'success': True, 'user': _camelize_dict(user_data)}

        if champion:
            champ_fields = {
                'champion_id': champion.champion_id,
                'full_name': champion.full_name,
                'email': champion.email,
                'phone_number': champion.phone_number,
                'county_sub_county': champion.county_sub_county,
                'date_of_birth': champion.date_of_birth.isoformat() if champion.date_of_birth else None,
                'gender': champion.gender,
            }
            out['champion'] = _camelize_dict(champ_fields)

        return jsonify(out), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Error updating profile')
        return jsonify({'error': str(e)}), 500


@api_bp.route('/auth/me/avatar', methods=['POST'])
@login_required
def api_auth_me_avatar():
    """Upload avatar for current authenticated user.

    Expects multipart/form-data with 'avatar' file field.
    Note: Avatar storage is not yet implemented in the User model.
    This endpoint is a placeholder to satisfy frontend contract.
    """
    import os

    if 'avatar' not in request.files:
        return jsonify({'error': 'No avatar file provided'}), 400

    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Validate file type
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        return jsonify({'error': f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'}), 400

    # Save to uploads folder
    uploads_dir = os.path.join(current_app.instance_path, 'uploads', 'avatars')
    os.makedirs(uploads_dir, exist_ok=True)

    filename = f'user_{current_user.user_id}.{ext}'
    filepath = os.path.join(uploads_dir, filename)
    file.save(filepath)

    # Return URL path (served statically or via a route)
    avatar_url = f'/uploads/avatars/{filename}'

    return jsonify({
        'success': True,
        'avatarUrl': avatar_url,
        'message': 'Avatar uploaded successfully'
    }), 200


@api_bp.route('/impact-stats', methods=['GET'])
def impact_stats():
    """
    Comprehensive impact statistics endpoint for UNDA Youth Network.
    Returns aggregated data about champions, youth support, training, and overall program impact.
    """
    
    # Champion Statistics
    total_champions = Champion.query.count()
    active_champions = Champion.query.filter_by(champion_status='Active').count()
    inactive_champions = Champion.query.filter_by(champion_status='Inactive').count()
    on_hold_champions = Champion.query.filter_by(champion_status='On Hold').count()
    
    # Youth Support Statistics
    total_youth_reached = db.session.query(
        func.sum(YouthSupport.number_of_youth_under_support)
    ).scalar() or 0
    
    total_reports = YouthSupport.query.count()
    
    # Average check-in completion rate
    avg_check_in_rate = db.session.query(
        func.avg(YouthSupport.weekly_check_in_completion_rate)
    ).scalar() or 0
    
    # Total screenings delivered
    total_screenings = db.session.query(
        func.sum(YouthSupport.monthly_mini_screenings_delivered)
    ).scalar() or 0
    
    # Total referrals
    total_referrals = RefferalPathway.query.count()
    total_referrals_initiated = db.session.query(
        func.sum(YouthSupport.referrals_initiated)
    ).scalar() or 0
    
    # Youth feedback and wellbeing
    avg_youth_feedback = db.session.query(
        func.avg(YouthSupport.youth_feedback_score)
    ).scalar() or 0
    
    avg_wellbeing_score = db.session.query(
        func.avg(YouthSupport.self_reported_wellbeing_check)
    ).scalar() or 0
    
    # Training Statistics
    total_trainings = TrainingRecord.query.count()
    
    # Safeguarding compliance
    safeguarding_completed = YouthSupport.query.filter_by(
        safeguarding_training_completed=True
    ).count()
    safeguarding_rate = (safeguarding_completed / total_reports * 100) if total_reports > 0 else 0
    
    # Consent compliance
    champions_with_consent = Champion.query.filter_by(consent_obtained=True).count()
    consent_rate = (champions_with_consent / total_champions * 100) if total_champions > 0 else 0
    
    # Risk Level Distribution
    high_risk_champions = Champion.query.filter_by(risk_level='High').count()
    medium_risk_champions = Champion.query.filter_by(risk_level='Medium').count()
    low_risk_champions = Champion.query.filter_by(risk_level='Low').count()
    
    # Gender Distribution
    gender_stats = db.session.query(
        Champion.gender,
        func.count(Champion.champion_id).label('count')
    ).filter(Champion.gender.isnot(None)).group_by(Champion.gender).all()
    
    gender_distribution = {gender: count for gender, count in gender_stats}
    
    # Recruitment Sources
    recruitment_sources = db.session.query(
        Champion.recruitment_source,
        func.count(Champion.champion_id).label('count')
    ).filter(Champion.recruitment_source.isnot(None)).group_by(Champion.recruitment_source).all()
    
    recruitment_distribution = {source: count for source, count in recruitment_sources}
    
    # Top Performing Champions (by youth reached)
    top_champions = db.session.query(
        Champion.champion_id,
        Champion.full_name,
        Champion.assigned_champion_code,
        func.sum(YouthSupport.number_of_youth_under_support).label('total_youth')
    ).join(
        YouthSupport, Champion.champion_id == YouthSupport.champion_id
    ).group_by(
        Champion.champion_id, Champion.full_name, Champion.assigned_champion_code
    ).order_by(
        func.sum(YouthSupport.number_of_youth_under_support).desc()
    ).limit(5).all()
    
    top_performers = [{
        'champion_id': c.champion_id,
        'name': c.full_name,
        'code': c.assigned_champion_code,
        'youth_reached': int(c.total_youth) if c.total_youth else 0
    } for c in top_champions]
    
    # User Statistics
    total_users = User.query.count()
    admin_users = User.query.filter_by(role=User.ROLE_ADMIN).count()
    supervisor_users = User.query.filter_by(role=User.ROLE_SUPERVISOR).count()
    # Count both 'Prevention Advocate' and legacy 'Champion' roles
    champion_users = User.query.filter(
        db.or_(User.role == User.ROLE_PREVENTION_ADVOCATE, User.role == 'Champion')
    ).count()
    
    # Event Statistics
    total_events = Event.query.count()
    upcoming_events = Event.query.filter_by(status='Upcoming').count()
    completed_events = Event.query.filter_by(status='Completed').count()
    
    # Blog Statistics
    total_blog_posts = BlogPost.query.count()
    published_posts = BlogPost.query.filter_by(published=True).count()
    total_blog_views = db.session.query(func.sum(BlogPost.views)).scalar() or 0
    
    # Recent Activity
    recent_reports = YouthSupport.query.order_by(
        YouthSupport.reporting_period.desc()
    ).limit(5).all()
    
    recent_activity = [{
        'report_id': r.support_id,
        'champion_id': r.champion_id,
        'reporting_period': r.reporting_period.isoformat() if r.reporting_period else None,
        'youth_under_support': r.number_of_youth_under_support
    } for r in recent_reports]
    
    # Compile comprehensive stats
    stats = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'overview': {
            'total_champions': total_champions,
            'active_champions': active_champions,
            'inactive_champions': inactive_champions,
            'on_hold_champions': on_hold_champions,
            'total_youth_reached': int(total_youth_reached),
            'total_reports': total_reports,
            'total_trainings': total_trainings,
            'total_referrals': total_referrals,
            'total_users': total_users,
            'total_events': total_events,
            'total_blog_posts': total_blog_posts
        },
        'performance_metrics': {
            'average_check_in_rate': round(float(avg_check_in_rate), 2),
            'total_screenings_delivered': int(total_screenings) if total_screenings else 0,
            'total_referrals_initiated': int(total_referrals_initiated) if total_referrals_initiated else 0,
            'average_youth_feedback_score': round(float(avg_youth_feedback), 2),
            'average_wellbeing_score': round(float(avg_wellbeing_score), 2)
        },
        'compliance': {
            'safeguarding_training_completion_rate': round(safeguarding_rate, 2),
            'consent_obtained_rate': round(consent_rate, 2)
        },
        'risk_distribution': {
            'high_risk': high_risk_champions,
            'medium_risk': medium_risk_champions,
            'low_risk': low_risk_champions
        },
        'demographics': {
            'gender_distribution': gender_distribution,
            'recruitment_sources': recruitment_distribution
        },
        'top_performers': top_performers,
        'user_breakdown': {
            'admins': admin_users,
            'supervisors': supervisor_users,
            'champions': champion_users
        },
        'content': {
            'upcoming_events': upcoming_events,
            'completed_events': completed_events,
            'published_blog_posts': published_posts,
            'total_blog_views': int(total_blog_views)
        },
        'recent_activity': recent_activity
    }
    
    return jsonify({
        'success': True,
        'stats': stats
    }), 200


@api_bp.route('/impact-stats/summary', methods=['GET'])
def impact_stats_summary():
    """
    Quick summary of key impact metrics.
    Lightweight endpoint for dashboard widgets.
    """
    total_champions = Champion.query.filter_by(champion_status='Active').count()
    total_youth_reached = db.session.query(
        func.sum(YouthSupport.number_of_youth_under_support)
    ).scalar() or 0
    total_trainings = TrainingRecord.query.count()
    total_referrals = RefferalPathway.query.count()
    
    return jsonify({
        'success': True,
        'summary': {
            'active_champions': total_champions,
            'youth_reached': int(total_youth_reached),
            'trainings_completed': total_trainings,
            'referrals_made': total_referrals,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
    }), 200


@api_bp.route('/campus-initiatives', methods=['GET', 'OPTIONS'])
def campus_initiatives():
    """Return public list of Campus Edition events."""
    try:
        events = Event.query.filter(Event.event_type == 'campus').order_by(Event.event_date.asc()).all()
        return jsonify({'success': True, 'events': [e.to_dict() for e in events]}), 200
    except Exception as e:
        current_app.logger.exception('Error fetching campus initiatives')
        return jsonify({'error': str(e)}), 500


@api_bp.route('/members/me', methods=['GET', 'OPTIONS'])
def get_current_member():
    """Return current authenticated member info for SPA dashboards."""
    from flask_login import current_user

    if not current_user.is_authenticated:
        return jsonify({'error': 'Unauthorized'}), 401

    return jsonify({
        'success': True,
        'user': {
            'user_id': current_user.user_id,
            'username': current_user.username,
            'email': current_user.email,
            'role': current_user.role,
            'champion_id': current_user.champion_id
        }
    }), 200


@api_bp.route('/members/me', methods=['PUT', 'OPTIONS'])
@api_auth_optional
def update_current_member():
    """Update current authenticated member profile."""
    # Accept JSON or multipart/form-data (e.g., when sending files). Normalize
    # incoming camelCase keys to snake_case so both frontend styles work.
    raw = None
    if request.is_json:
        raw = request.get_json() or {}
    else:
        # request.form handles application/x-www-form-urlencoded and multipart/form-data
        try:
            raw = request.form.to_dict() or {}
        except Exception:
            raw = {}

    # Normalize camelCase to snake_case if helper available
    try:
        from blueprints.public_auth import normalize_input
        data = normalize_input(raw or {})
    except Exception:
        data = raw or {}
    # Determine acting user: prefer session user, otherwise require `user_id` in payload when using API token
    if current_user and current_user.is_authenticated:
        user = current_user
    else:
        if not _check_api_token():
            return jsonify({'error': 'Unauthorized'}), 401
        uid = data.get('user_id')
        if not uid:
            return jsonify({'error': 'Missing user_id for token-authenticated request'}), 400
        user = db.session.get(User, int(uid))
        if not user:
            return jsonify({'error': 'User not found'}), 404

    # Allow updating a small set of profile fields
    allowed = ['email', 'username', 'full_name', 'date_of_birth', 'phone_number', 'county_sub_county']

    try:
        if 'email' in data and data['email']:
            if not validate_email(data['email']):
                return jsonify({'error': 'Invalid email format'}), 400
            user.email = data['email']

        if 'username' in data and data['username']:
            # ensure uniqueness
            existing = User.query.filter(User.username == data['username'], User.user_id != user.user_id).first()
            if existing:
                return jsonify({'error': 'Username already taken'}), 409
            user.username = data['username']

        # Accept and persist profile-like fields on the user record as well
        # so GET endpoints reflect values even when no Champion profile exists.
        if 'date_of_birth' in data and data['date_of_birth']:
            try:
                user.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
            except Exception:
                # ignore here; champion date parsing handles format errors for champion records
                pass
        if 'gender' in data and data['gender']:
            user.gender = data['gender']
        if 'county_sub_county' in data and data['county_sub_county']:
            user.county_sub_county = data['county_sub_county']

        # Update champion profile fields when user is a Prevention Advocate and linked to champion
        champion = None
        if user.champion_id:
                champion = db.session.get(Champion, user.champion_id)

        if champion:
            if 'full_name' in data and data['full_name']:
                champion.full_name = data['full_name']
            if 'date_of_birth' in data and data['date_of_birth']:
                try:
                    champion.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
                except Exception:
                    return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
            if 'phone_number' in data and data['phone_number']:
                if normalize_phone:
                    normalized = normalize_phone(data['phone_number'])
                    if not normalized:
                        return jsonify({'error': 'Invalid phone number'}), 400
                    champion.phone_number = normalized
                else:
                    champion.phone_number = data['phone_number']
            if 'county_sub_county' in data and data['county_sub_county']:
                champion.county_sub_county = data['county_sub_county']

        db.session.add(user)
        if champion:
            db.session.add(champion)
        db.session.commit()

        return jsonify({'success': True, 'user': {
            'user_id': user.user_id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'champion_id': user.champion_id
        }}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Error updating current member')
        return jsonify({'error': str(e)}), 500


@api_bp.route('/checkin', methods=['POST'])
@api_auth_optional
def submit_checkin():
    """Submit or update a weekly check-in report for a champion.

    Expected JSON: { 'reporting_period': 'YYYY-MM-DD', 'number_of_youth_under_support': int,
    'weekly_check_in_completion_rate': float, 'monthly_mini_screenings_delivered': int,
    'referrals_initiated': int, 'flags_and_concerns_logged': str }
    """
    data = request.get_json() or {}

    # Determine champion: prefer current user's champion profile
    champion = None
    if current_user and current_user.is_authenticated and current_user.champion_id:
        champion = db.session.get(Champion, current_user.champion_id)
    elif hasattr(g, 'jwt_payload') and g.jwt_payload:
        # JWT token auth - get user from token's sub claim
        user_id = g.jwt_payload.get('sub')
        if user_id:
            user = db.session.get(User, int(user_id))
            if user and user.champion_id:
                champion = db.session.get(Champion, user.champion_id)
        # Fallback: allow champion_id in payload for automation scripts
        if not champion:
            cid = data.get('champion_id')
            if cid:
                champion = db.session.get(Champion, int(cid))
    else:
        # Legacy API token auth - require champion_id in payload
        cid = data.get('champion_id')
        if cid:
            champion = db.session.get(Champion, int(cid))

    if not champion:
        return jsonify({'error': 'Champion profile not found for current user'}), 404

    # Parse reporting_period
    rp = data.get('reporting_period')
    if not rp:
        reporting_period = date.today()
    else:
        try:
            reporting_period = datetime.strptime(rp, '%Y-%m-%d').date()
        except Exception:
            return jsonify({'error': 'Invalid reporting_period format. Use YYYY-MM-DD'}), 400

    # Token-based checkins are handled by the token-only blueprint (api_token_bp)
    # which enforces stricter token + JSON checks. For authenticated session users
    # we keep the ability to submit via the same URL but only if logged in.
    try:
        # Find existing or create new record (session-auth flow)
        report = YouthSupport.query.filter_by(champion_id=champion.champion_id, reporting_period=reporting_period).first()
        if not report:
            report = YouthSupport(champion_id=champion.champion_id, reporting_period=reporting_period)

        if 'number_of_youth_under_support' in data:
            report.number_of_youth_under_support = int(data.get('number_of_youth_under_support') or 0)
        if 'weekly_check_in_completion_rate' in data:
            report.weekly_check_in_completion_rate = float(data.get('weekly_check_in_completion_rate') or 0)
        if 'monthly_mini_screenings_delivered' in data:
            report.monthly_mini_screenings_delivered = int(data.get('monthly_mini_screenings_delivered') or 0)
        if 'referrals_initiated' in data:
            report.referrals_initiated = int(data.get('referrals_initiated') or 0)
        if 'flags_and_concerns_logged' in data:
            report.flags_and_concerns_logged = data.get('flags_and_concerns_logged')

        # Red-flag logic remains the same
        try:
            if report.weekly_check_in_completion_rate is not None and float(report.weekly_check_in_completion_rate) < 50:
                report.flag_timestamp = datetime.now(timezone.utc)
            if report.flags_and_concerns_logged:
                report.flag_timestamp = datetime.now(timezone.utc)
        except Exception:
            pass

        db.session.add(report)
        db.session.commit()

        return jsonify({'success': True, 'report_id': report.support_id, 'flagged': bool(report.flag_timestamp)}), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Error submitting check-in')
        return jsonify({'error': str(e)}), 500
