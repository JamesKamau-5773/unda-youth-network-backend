from flask import Blueprint, jsonify, redirect, request
import os
from flask_login import login_required, current_user
from decorators import champion_required


champion_bp = Blueprint('champion', __name__, url_prefix='/champion')


@champion_bp.route('/dashboard', methods=['GET'])
@login_required
@champion_required
def dashboard():
    """
    Legacy server-rendered dashboard route.
    The champion dashboard is now served by the frontend SPA.
    Redirect browser requests to the frontend; return JSON for API clients.
    """
    # Check if this is an API/XHR request
    if request.is_json or request.headers.get('Accept', '').startswith('application/json'):
        return jsonify({
            'message': 'Champion dashboard has moved to the frontend SPA',
            'redirect': os.environ.get('FRONTEND_URL', 'https://undayouth.org') + '/dashboard'
        }), 200

    # Browser request: redirect to frontend
    frontend_url = os.environ.get('FRONTEND_URL', 'https://undayouth.org')
    return redirect(f"{frontend_url}/dashboard")


@champion_bp.route('/submit-report', methods=['POST'])
@login_required
@champion_required
def submit_report():
    """
    Legacy server-rendered report submission route.
    Report submission is now handled via POST /api/checkin.
    Return JSON directing clients to use the API endpoint.
    """
    return jsonify({
        'error': 'This endpoint is deprecated',
        'message': 'Use POST /api/checkin to submit weekly check-in reports',
        'api_endpoint': '/api/checkin'
    }), 410  # 410 Gone

