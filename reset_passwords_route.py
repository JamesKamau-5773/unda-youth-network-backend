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
    Create or reset passwords for admin, supervisor1, and alice.
    Access via: https://your-app.onrender.com/reset-production-passwords/YOUR_SECRET
    """
    # Verify secret
    if secret != RESET_SECRET:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        results = []
        
        # Create or reset admin
        admin = User.query.filter_by(username='admin').first()
        if admin:
            admin.password_hash = hash_password('Admin@123')
            admin.failed_login_attempts = 0
            admin.account_locked = False
            admin.locked_until = None
            results.append('✓ Admin password reset to: Admin@123')
        else:
            admin = User(
                username='admin',
                role='Admin',
                password_hash=hash_password('Admin@123')
            )
            db.session.add(admin)
            results.append('✓ Admin user created with password: Admin@123')
        
        # Create or reset supervisor1
        supervisor = User.query.filter_by(username='supervisor1').first()
        if supervisor:
            supervisor.password_hash = hash_password('Super@123')
            supervisor.failed_login_attempts = 0
            supervisor.account_locked = False
            supervisor.locked_until = None
            results.append('✓ Supervisor1 password reset to: Super@123')
        else:
            supervisor = User(
                username='supervisor1',
                role='Supervisor',
                password_hash=hash_password('Super@123')
            )
            db.session.add(supervisor)
            results.append('✓ Supervisor1 user created with password: Super@123')
        
        # Create or reset alice
        alice = User.query.filter_by(username='alice').first()
        if alice:
            alice.password_hash = hash_password('Alice@123')
            alice.failed_login_attempts = 0
            alice.account_locked = False
            alice.locked_until = None
            results.append('✓ Alice password reset to: Alice@123')
        else:
            alice = User(
                username='alice',
                role='Champion',
                password_hash=hash_password('Alice@123')
            )
            db.session.add(alice)
            results.append('✓ Alice user created with password: Alice@123')
        
        # Commit changes
        db.session.commit()
        results.append('\n✓ All changes committed successfully!')
        
        return jsonify({
            'success': True,
            'message': 'Users created/passwords reset successfully',
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
