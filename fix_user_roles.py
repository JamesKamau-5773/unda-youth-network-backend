#!/usr/bin/env python3
"""
Script to validate and fix all user roles in the database.
This ensures no users have invalid roles that could cause redirect loops.
"""

from app import create_app
from models import db, User

def fix_user_roles():
    """Validate and normalize all user roles in the database."""
    app, _ = create_app()
    
    with app.app_context():
        print("Checking all user roles...")
        users = User.query.all()
        
        fixed_count = 0
        invalid_users = []
        
        for user in users:
            original_role = user.role
            
            try:
                # Validate and normalize the role
                user.validate_role()
                
                if original_role != user.role:
                    print(f"✓ Fixed: {user.username} - '{original_role}' → '{user.role}'")
                    fixed_count += 1
                else:
                    print(f"✓ Valid: {user.username} - '{user.role}'")
                    
            except ValueError as e:
                print(f"✗ Invalid: {user.username} - '{original_role}' - {str(e)}")
                invalid_users.append((user, original_role))
        
        if invalid_users:
            print(f"\n{len(invalid_users)} users with invalid roles found:")
            for user, role in invalid_users:
                print(f"  - {user.username}: '{role}'")
            print("\nPlease manually update these users or delete them.")
            response = input("\nSet all invalid roles to 'Champion'? (y/n): ")
            
            if response.lower() == 'y':
                for user, _ in invalid_users:
                    user.role = 'Champion'
                    print(f"  Set {user.username} → Champion")
                    fixed_count += 1
        
        if fixed_count > 0:
            db.session.commit()
            print(f"\n✓ Fixed {fixed_count} user roles successfully!")
        else:
            print("\n✓ All user roles are valid!")
        
        # Display summary
        print("\n=== Role Summary ===")
        for role in User.VALID_ROLES:
            count = User.query.filter(User.role == role).count()
            print(f"{role}: {count} users")

if __name__ == '__main__':
    fix_user_roles()
