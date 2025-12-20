#!/usr/bin/env python3
"""
Password Reset Script for Production Database
Run this script on Render shell to reset user passwords.

Usage:
    python reset_production_passwords.py
"""

from app import app, db
from models import User, hash_password

def reset_passwords():
    """Reset passwords for admin, supervisor1, and alice accounts."""
    with app.app_context():
        print("Starting password reset...")
        
        # Reset admin password
        admin = User.query.filter_by(username='admin').first()
        if admin:
            admin.password_hash = hash_password('Admin@123')
            admin.failed_login_attempts = 0
            admin.account_locked = False
            admin.locked_until = None
            print("✓ Admin password reset to: Admin@123")
        else:
            print("✗ Admin user not found")
        
        # Reset supervisor1 password
        supervisor = User.query.filter_by(username='supervisor1').first()
        if supervisor:
            supervisor.password_hash = hash_password('Super@123')
            supervisor.failed_login_attempts = 0
            supervisor.account_locked = False
            supervisor.locked_until = None
            print("✓ Supervisor1 password reset to: Super@123")
        else:
            print("✗ Supervisor1 user not found")
        
        # Reset alice password
        alice = User.query.filter_by(username='alice').first()
        if alice:
            alice.password_hash = hash_password('Alice@123')
            alice.failed_login_attempts = 0
            alice.account_locked = False
            alice.locked_until = None
            print("✓ Alice password reset to: Alice@123")
        else:
            print("✗ Alice user not found")
        
        # Commit changes
        try:
            db.session.commit()
            print("\n✓ All changes committed successfully!")
            print("\nCredentials:")
            print("  admin / Admin@123")
            print("  supervisor1 / Super@123")
            print("  alice / Alice@123")
        except Exception as e:
            db.session.rollback()
            print(f"\n✗ Error committing changes: {e}")
            return False
        
        return True

if __name__ == '__main__':
    success = reset_passwords()
    exit(0 if success else 1)
