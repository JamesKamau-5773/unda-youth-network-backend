"""
API Status and Health Check Endpoints
For frontend integration testing
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import db, User, Champion, MentalHealthAssessment
from datetime import datetime, timezone

api_status_bp = Blueprint('api_status', __name__, url_prefix='/api')


@api_status_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint - no authentication required
    Frontend can use this to verify backend is accessible
    """
    try:
        # Check database connection
        db.session.execute('SELECT 1')
        db_status = 'healthy'
    except Exception as e:
        db_status = f'unhealthy: {str(e)}'
    
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'service': 'UMV Backend API',
        'version': '2.0.0-privacy-first',
        'database': db_status
    }), 200


@api_status_bp.route('/status', methods=['GET'])
def api_status():
    """
    Detailed API status - no authentication required
    Shows available endpoints and system information
    """
    try:
        # Get counts
        total_users = User.query.count()
        total_champions = Champion.query.count()
        total_assessments = MentalHealthAssessment.query.count()
        
        # Count by role
        admins = User.query.filter_by(role=User.ROLE_ADMIN).count()
        supervisors = User.query.filter_by(role=User.ROLE_SUPERVISOR).count()
        advocates = User.query.filter_by(role='Prevention Advocate').count()
        
        stats_available = True
    except Exception as e:
        total_users = total_champions = total_assessments = 0
        admins = supervisors = advocates = 0
        stats_available = False
    
    return jsonify({
        'status': 'operational',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'api_version': '2.0.0',
        'privacy_mode': 'enabled',
        'features': {
            'champion_registration': True,
            'mental_health_screening': True,
            'privacy_first_assessments': True,
            'auto_referrals': True,
            'role_based_access': True
        },
        'statistics': {
            'total_users': total_users,
            'total_champions': total_champions,
            'total_assessments': total_assessments,
            'roles': {
                'admins': admins,
                'supervisors': supervisors,
                'prevention_advocates': advocates
            }
        } if stats_available else None,
        'endpoints': {
            'public': [
                'POST /api/champions/register - Champion self-registration',
                'POST /api/champions/verify-code - Verify champion code',
                'POST /api/auth/register - Member registration',
                'POST /auth/login - User login'
            ],
            'prevention_advocate': [
                'POST /api/assessments/submit - Submit mental health assessment',
                'GET /api/assessments/my-submissions - View own submissions',
                'POST /api/assessments/validate-champion-code - Validate code'
            ],
            'supervisor': [
                'GET /api/assessments/dashboard - View aggregated statistics',
                'GET /api/assessments/statistics - Comprehensive statistics',
                'GET /api/assessments/by-advocate - Advocate performance'
            ],
            'admin': [
                'GET /api/assessments/admin/overview - System-wide overview',
                'All supervisor endpoints',
                'All prevention advocate endpoints'
            ]
        }
    }), 200


@api_status_bp.route('/me', methods=['GET'])
@login_required
def current_user_info():
    """
    Get current authenticated user information
    Useful for frontend to display user details
    """
    return jsonify({
        'success': True,
        'user': {
            'user_id': current_user.user_id,
            'username': current_user.username,
            'role': current_user.role,
            'champion_id': current_user.champion_id
        }
    }), 200


@api_status_bp.route('/cors-test', methods=['GET', 'POST', 'OPTIONS'])
def cors_test():
    """
    CORS test endpoint
    Frontend can use this to verify CORS is working
    """
    return jsonify({
        'success': True,
        'message': 'CORS is working correctly',
        'method': request.method,
        'origin': request.headers.get('Origin', 'No origin header'),
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200
