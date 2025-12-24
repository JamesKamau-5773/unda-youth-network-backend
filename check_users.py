#!/usr/bin/env python3
"""Script to check all users in the production database"""
import os
from app import create_app
from models import db, User

app = create_app()

with app.app_context():
    print("\n=== PRODUCTION DATABASE USER CHECK ===\n")
    
    users = User.query.all()
    print(f"Total users in database: {len(users)}\n")
    
    if len(users) == 0:
        print("⚠️  NO USERS FOUND IN DATABASE!")
        print("\nCreating test users now...\n")
        
        # Create admin user
        admin = User(username='admin')
        admin.set_role('Admin')
        admin.set_password('Admin123!')
        db.session.add(admin)
        
        # Create supervisor user
        supervisor = User(username='supervisor')
        supervisor.set_role('Supervisor')
        supervisor.set_password('Supervisor123!')
        db.session.add(supervisor)
        
        # Create champion user (alice)
        alice = User(username='alice', champion_id=1)
        alice.set_role('Champion')
        alice.set_password('TestPassword123!')
        db.session.add(alice)
        
        db.session.commit()
        print("✅ Created 3 test users:")
        print("   - admin / Admin123!")
        print("   - supervisor / Supervisor123!")
        print("   - alice / TestPassword123!")
        
        # Re-query to show created users
        users = User.query.all()
    
    print("\nAll users in database:")
    print("-" * 80)
    for user in users:
        print(f"ID: {user.user_id}")
        print(f"Username: {user.username}")
        print(f"Role: {user.role}")
        print(f"Champion ID: {user.champion_id}")
        print(f"Locked: {user.is_locked()}")
        print(f"Failed Login Attempts: {user.failed_login_attempts}")
        print("-" * 80)
    
    # Test password verification
    print("\n=== PASSWORD VERIFICATION TEST ===\n")
    test_credentials = [
        ('admin', 'Admin123!'),
        ('supervisor', 'Supervisor123!'),
        ('alice', 'TestPassword123!'),
        ('supervisor1', 'Supervisor123!'),
    ]
    
    for username, password in test_credentials:
        user = User.query.filter_by(username=username).first()
        if user:
            is_valid = user.check_password(password)
            status = "✅ VALID" if is_valid else "❌ INVALID"
            print(f"{username} / {password}: {status}")
        else:
            print(f"{username}: ❌ USER NOT FOUND")
    
    print("\n" + "=" * 80)
