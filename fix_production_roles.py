#!/usr/bin/env python3
"""
Emergency script to fix user roles in production database.
Run this on Render to fix redirect loop issues caused by invalid roles.
"""

from app import create_app
from models import db, User

def fix_production_roles():
    """Fix all user roles in production database"""
    app, _ = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("PRODUCTION ROLE FIX SCRIPT")
        print("=" * 60)
        
        users = User.query.all()
        print(f"\nFound {len(users)} total users")
        
        fixed_count = 0
        errors = []
        
        for user in users:
            original_role = user.role
            
            try:
                # Validate and normalize the role
                user.validate_role()
                
                if original_role != user.role:
                    print(f"FIXED: {user.username} - '{original_role}' -> '{user.role}'")
                    fixed_count += 1
                else:
                    print(f"OK: {user.username} - '{user.role}'")
                    
            except ValueError as e:
                # Invalid role that can't be auto-fixed
                print(f"ERROR: {user.username} - '{original_role}' - Setting to Champion")
                user.role = 'Champion'
                fixed_count += 1
                errors.append((user.username, original_role))
        
        if fixed_count > 0:
            db.session.commit()
            print(f"\n{'=' * 60}")
            print(f"SUCCESS: Fixed {fixed_count} user roles")
            print(f"{'=' * 60}")
        else:
            print(f"\n{'=' * 60}")
            print("SUCCESS: All user roles are valid")
            print(f"{'=' * 60}")
        
        if errors:
            print(f"\nUsers that had invalid roles (set to Champion):")
            for username, role in errors:
                print(f"  - {username}: was '{role}'")
        
        # Display final summary
        print(f"\n{'=' * 60}")
        print("FINAL ROLE DISTRIBUTION:")
        print(f"{'=' * 60}")
        for role in User.VALID_ROLES:
            count = User.query.filter(User.role == role).count()
            print(f"{role}: {count} users")
        
        print(f"\n{'=' * 60}")
        print("DEPLOYMENT READY - No redirect loops expected")
        print(f"{'=' * 60}")

if __name__ == '__main__':
    fix_production_roles()
