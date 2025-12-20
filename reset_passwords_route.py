"""
One-time password reset route for production deployment.
Add this to your app temporarily, deploy, trigger the reset, then remove it.
"""

from flask import Blueprint, jsonify
from models import User, Champion, YouthSupport, hash_password, db
import os

# Create blueprint
reset_bp = Blueprint('reset', __name__)

# Secret key to prevent unauthorized access
RESET_SECRET = os.environ.get('RESET_SECRET', 'change-this-secret-key')

@reset_bp.route('/check-database/<secret>')
def check_database(secret):
    """Check what's in the production database."""
    if secret != RESET_SECRET:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        users = User.query.all()
        champions = Champion.query.all()
        supports = YouthSupport.query.all()
        
        return jsonify({
            'users': [{'username': u.username, 'role': u.role, 'user_id': u.user_id, 'champion_id': u.champion_id} for u in users],
            'champions_count': len(champions),
            'supports_count': len(supports),
            'total_users': len(users)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reset_bp.route('/init-database/<secret>')
def init_database(secret):
    """Initialize the production database with correct schema."""
    if secret != RESET_SECRET:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Drop all tables and recreate them with the current schema
        db.drop_all()
        db.create_all()
        
        # Create initial admin user
        admin = User(
            username='admin',
            role='Admin',
            password_hash=hash_password('Admin@123')
        )
        db.session.add(admin)
        
        # Create supervisor user
        supervisor = User(
            username='supervisor1',
            role='Supervisor',
            password_hash=hash_password('Super@123')
        )
        db.session.add(supervisor)
        
        # Create champion user
        alice_user = User(
            username='alice',
            role='Champion',
            password_hash=hash_password('Alice@123')
        )
        db.session.add(alice_user)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Database initialized successfully',
            'users_created': ['admin', 'supervisor1', 'alice'],
            'credentials': {
                'admin': 'Admin@123',
                'supervisor1': 'Super@123',
                'alice': 'Alice@123'
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'success': False}), 500

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
