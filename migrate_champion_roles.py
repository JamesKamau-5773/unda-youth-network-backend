#!/usr/bin/env python3
"""
Migrate Champion roles to Prevention Advocate
Converts all users with role='Champion' to role='Prevention Advocate'
"""

from app import app
from models import User, db

def migrate_champion_roles():
    """Update all Champion roles to Prevention Advocate"""
    with app.app_context():
        # Find all users with Champion role
        champions = User.query.filter_by(role='Champion').all()
        
        if not champions:
            print("✅ No Champion roles found - database is already up to date")
            return
        
        print(f"Found {len(champions)} users with 'Champion' role:")
        print("-" * 60)
        
        # Update each user
        for user in champions:
            old_role = user.role
            user.set_role(User.ROLE_PREVENTION_ADVOCATE)
            print(f"  {user.username:20s} | {old_role} → {user.role}")
        
        # Commit changes
        try:
            db.session.commit()
            print("-" * 60)
            print(f"✅ Successfully migrated {len(champions)} users")
            print(f"   All 'Champion' roles → 'Prevention Advocate'")
            
            # Verify migration
            remaining = User.query.filter_by(role='Champion').count()
            if remaining == 0:
                print("✅ Migration verified - no Champion roles remain")
            else:
                print(f"⚠️  Warning: {remaining} Champion roles still exist")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration failed: {str(e)}")
            raise

if __name__ == '__main__':
    print("=" * 60)
    print("Champion → Prevention Advocate Role Migration")
    print("=" * 60)
    migrate_champion_roles()
    print("=" * 60)
