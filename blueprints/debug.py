from flask import Blueprint, jsonify, current_app, request
from flask_login import login_required, current_user

debug_bp = Blueprint('debug', __name__, url_prefix='/admin/api')


@debug_bp.route('/cookie-info', methods=['GET'])
@login_required
def cookie_info():
    # Admin-only sensitive endpoint: require admin role check in caller
    role = getattr(current_user, 'role', None)
    if role != 'Admin':
        return jsonify({'error': 'Forbidden'}), 403

    cfg = {
        'session_cookie_domain': current_app.config.get('SESSION_COOKIE_DOMAIN'),
        'cors_origins': current_app.config.get('CORS_ORIGINS') or current_app.config.get('CORS_ORIGINS_PARAM'),
        'frontend_origin_env': current_app.config.get('FRONTEND_ORIGIN') or None,
        'request_host': request.host
    }
    return jsonify(cfg), 200
