#!/usr/bin/env python3
"""
Remove test email from database
"""
from app import app
from models import User, Champion, db

def remove_email(email_to_remove):
    """Remove all records with specified email"""
    with app.app_context():
        print(f"Searching for email: {email_to_remove}")
        print("=" * 60)
        
        # Find users with this email
        users = User.query.filter_by(email=email_to_remove).all()
        if users:
            print(f"Found {len(users)} user(s) with this email:")
            for user in users:
                print(f"  - User ID: {user.user_id}, Username: {user.username}, Role: {user.role}")
        
        # Find champions with this email
        champions = Champion.query.filter_by(email=email_to_remove).all()
        if champions:
            print(f"Found {len(champions)} champion(s) with this email:")
            for champ in champions:
                print(f"  - Champion ID: {champ.champion_id}, Name: {champ.full_name}, Code: {champ.assigned_champion_code}")
        
        if not users and not champions:
            print(f"No records found with email: {email_to_remove}")
            return
        
        # Confirm deletion
        print("=" * 60)
        confirm = input("Delete these records? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            print("Deletion cancelled")
            return
        
        # Delete users and their associated champions
        deleted_users = 0
        deleted_champions = 0
        
        for user in users:
            # Delete associated champion if exists
            if user.champion_id:
                champion = Champion.query.get(user.champion_id)
                if champion:
                    db.session.delete(champion)
                    deleted_champions += 1
                    print(f"✓ Deleted champion: {champion.full_name}")
            
            db.session.delete(user)
            deleted_users += 1
            print(f"✓ Deleted user: {user.username}")
        
        # Delete standalone champions (not linked to users)
        for champ in champions:
            if champ not in [Champion.query.get(u.champion_id) for u in users if u.champion_id]:
                db.session.delete(champ)
                deleted_champions += 1
                print(f"✓ Deleted champion: {champ.full_name}")
        
        db.session.commit()
        print("=" * 60)
        print(f"✓ Successfully deleted {deleted_users} user(s) and {deleted_champions} champion(s)")
        print(f"Email {email_to_remove} is now available for testing")

if __name__ == '__main__':
    email = "jamesnk5773@gmail.com"
    remove_email(email)
