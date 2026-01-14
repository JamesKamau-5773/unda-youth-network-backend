#!/usr/bin/env python3
"""
Script to remove test emails from PRODUCTION database on Render
WARNING: This modifies production data!
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Get production database URL from environment variable
prod_db_url = os.environ.get('PRODUCTION_DATABASE_URL')

if not prod_db_url:
    print("ERROR: PRODUCTION_DATABASE_URL environment variable not set")
    print("\nPlease set it with:")
    print('export PRODUCTION_DATABASE_URL="your-render-postgres-url"')
    exit(1)

# Fix postgres:// to postgresql:// if needed
if prod_db_url.startswith('postgres://'):
    prod_db_url = prod_db_url.replace('postgres://', 'postgresql://', 1)

emails_to_remove = ['jamesnk5773@gmail.com', 'gpjohhnny@gmail.com']

print("=" * 60)
print("PRODUCTION DATABASE CLEANUP")
print("=" * 60)
print(f"Database: {prod_db_url.split('@')[1] if '@' in prod_db_url else 'Unknown'}")
print(f"Emails to remove: {', '.join(emails_to_remove)}")
print("=" * 60)

# Confirm (unless --yes flag is provided)
if '--yes' not in sys.argv:
    response = input("\nThis will DELETE data from PRODUCTION. Type 'YES' to confirm: ")
    if response != 'YES':
        print("Aborted.")
        exit(0)
else:
    print("\n--yes flag provided, proceeding with deletion...")

# Create engine and session
engine = create_engine(prod_db_url)
Session = sessionmaker(bind=engine)
session = Session()

try:
    for email in emails_to_remove:
        print(f"\n--- Processing {email} ---")
        
        # Find and delete from Champions table
        result = session.execute(
            text("SELECT champion_id, full_name, assigned_champion_code FROM champions WHERE email = :email"),
            {"email": email}
        )
        champions = result.fetchall()
        
        print(f"Champions found: {len(champions)}")
        for champ in champions:
            print(f"  - {champ.full_name} (ID: {champ.champion_id}, Code: {champ.assigned_champion_code})")
            
            # Delete associated User first
            user_result = session.execute(
                text("SELECT user_id, username FROM users WHERE champion_id = :champ_id"),
                {"champ_id": champ.champion_id}
            )
            users = user_result.fetchall()
            for user in users:
                print(f"    Deleting user: {user.username} (ID: {user.user_id})")
                session.execute(
                    text("DELETE FROM users WHERE user_id = :user_id"),
                    {"user_id": user.user_id}
                )
            
            # Delete champion
            session.execute(
                text("DELETE FROM champions WHERE champion_id = :champ_id"),
                {"champ_id": champ.champion_id}
            )
        
        # Find and delete from Users table (in case email is only in users)
        result = session.execute(
            text("SELECT user_id, username FROM users WHERE email = :email"),
            {"email": email}
        )
        users = result.fetchall()
        
        print(f"Users found: {len(users)}")
        for user in users:
            print(f"  - {user.username} (ID: {user.user_id})")
            session.execute(
                text("DELETE FROM users WHERE user_id = :user_id"),
                {"user_id": user.user_id}
            )
    
    # Commit all deletions
    session.commit()
    print("\n" + "=" * 60)
    print("SUCCESS: All test emails removed from production database")
    print("=" * 60)
    
except Exception as e:
    session.rollback()
    print(f"\nERROR: {e}")
    print("Changes rolled back.")
    exit(1)
    
finally:
    session.close()
