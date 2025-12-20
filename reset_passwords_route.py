"""
One-time password reset route for production deployment.
Add this to your app temporarily, deploy, trigger the reset, then remove it.
"""

from flask import Blueprint, jsonify
from models import User, hash_password, db
import os

# Create blueprint
reset_bp = Blueprint('reset', __name__)

# Secret key to prevent unauthorized access
RESET_SECRET = os.environ.get('RESET_SECRET', 'change-this-secret-key')

@reset_bp.route('/reset-production-passwords/<secret>')
def reset_production_passwords(secret):
    """
    Reset passwords for admin, supervisor1, and alice.
    Access via: https://your-app.onrender.com/reset-production-passwords/YOUR_SECRET
    """
    # Verify secret
    if secret != RESET_SECRET:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        results = []
        
        # Reset admin password
        admin = User.query.filter_by(username='admin').first()
        if admin:
            admin.password_hash = hash_password('Admin@123')
            admin.failed_login_attempts = 0
            admin.account_locked = False
            admin.locked_until = None
            results.append('✓ Admin password reset to: Admin@123')
        else:
            results.append('✗ Admin user not found')
        
        # Reset supervisor1 password
        supervisor = User.query.filter_by(username='supervisor1').first()
        if supervisor:
            supervisor.password_hash = hash_password('Super@123')
            supervisor.failed_login_attempts = 0
            supervisor.account_locked = False
            supervisor.locked_until = None
            results.append('✓ Supervisor1 password reset to: Super@123')
        else:
            results.append('✗ Supervisor1 user not found')
        
        # Reset alice password
        alice = User.query.filter_by(username='alice').first()
        if alice:
            alice.password_hash = hash_password('Alice@123')
            alice.failed_login_attempts = 0
            alice.account_locked = False
            alice.locked_until = None
            results.append('✓ Alice password reset to: Alice@123')
        else:
            results.append('✗ Alice user not found')
        
        # Commit changes
        db.session.commit()
        results.append('\n✓ All changes committed successfully!')
        
        return jsonify({
            'success': True,
            'message': 'Passwords reset successfully',
            'details': results,
            'credentials': {
                'admin': 'Admin@123',
                'supervisor1': 'Super@123',
                'alice': 'Alice@123'
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
