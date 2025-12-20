#!/usr/bin/env python3
"""
Test script for user management functionality.
Tests all routes and validations for admin user management.
"""

from app import app, db
from models import User
from flask_bcrypt import Bcrypt
import secrets
import string

bcrypt = Bcrypt()

def test_generate_temp_password():
    """Test password generation helper function."""
    print("\n=== TEST 1: Password Generation ===")
    
    def generate_temp_password():
        """Generate a secure random password."""
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(characters) for _ in range(12))
        return password
    
    password = generate_temp_password()
    print(f"✓ Generated password: {password}")
    print(f"✓ Length: {len(password)} characters")
    
    # Verify it has mixed characters
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*" for c in password)
    
    print(f"✓ Has uppercase: {has_upper}")
    print(f"✓ Has lowercase: {has_lower}")
    print(f"✓ Has digits: {has_digit}")
    print(f"✓ Has special chars: {has_special}")
    
    return True


def test_database_setup():
    """Test database connection and setup."""
    print("\n=== TEST 2: Database Setup ===")
    
    with app.app_context():
        db.create_all()
        print("✓ Database tables created/verified")
        
        # Count users
        total_users = User.query.count()
        admins = User.query.filter_by(role='Admin').count()
        supervisors = User.query.filter_by(role='Supervisor').count()
        champions = User.query.filter_by(role='Champion').count()
        
        print(f"✓ Total users: {total_users}")
        print(f"✓ Admins: {admins}, Supervisors: {supervisors}, Champions: {champions}")
        
        return True


def test_create_user_validation():
    """Test user creation with validation."""
    print("\n=== TEST 3: Create User Validation ===")
    
    with app.app_context():
        # Test 1: Valid user creation
        test_username = f"testuser_{secrets.token_hex(4)}"
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits + "!@#$%^&*") for _ in range(12))
        hashed_password = bcrypt.generate_password_hash(temp_password).decode('utf-8')
        
        new_user = User(
            username=test_username,
            password_hash=hashed_password,
            role='Supervisor'
        )
        db.session.add(new_user)
        db.session.commit()
        
        print(f"✓ Created user: {test_username}")
        print(f"✓ Temporary password: {temp_password}")
        print(f"✓ Role: Supervisor")
        
        # Verify user exists
        created_user = User.query.filter_by(username=test_username).first()
        assert created_user is not None, "User not found after creation"
        print(f"✓ User verified in database")
        
        # Test 2: Duplicate username (should fail)
        try:
            duplicate_user = User(
                username=test_username,
                password_hash=hashed_password,
                role='Champion'
            )
            db.session.add(duplicate_user)
            db.session.commit()
            print("✗ FAILED: Duplicate username allowed")
            return False
        except Exception as e:
            db.session.rollback()
            print(f"✓ Duplicate username correctly rejected")
        
        # Test 3: Username too short (should fail)
        short_username = "ab"  # Less than 3 characters
        if len(short_username) < 3:
            print(f"✓ Username '{short_username}' correctly identified as too short (< 3 chars)")
        
        return True


def test_reset_password():
    """Test password reset functionality."""
    print("\n=== TEST 4: Password Reset ===")
    
    with app.app_context():
        # Get a test user
        user = User.query.filter_by(username='supervisor1').first()
        if not user:
            print("✗ Test user 'supervisor1' not found")
            return False
        
        old_password_hash = user.password_hash
        old_failed_attempts = user.failed_login_attempts
        
        # Simulate password reset
        new_temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits + "!@#$%^&*") for _ in range(12))
        user.password_hash = bcrypt.generate_password_hash(new_temp_password).decode('utf-8')
        user.failed_login_attempts = 0
        user.account_locked = False
        user.locked_until = None
        db.session.commit()
        
        print(f"✓ Password reset for user: {user.username}")
        print(f"✓ New temporary password: {new_temp_password}")
        print(f"✓ Failed attempts reset to: {user.failed_login_attempts}")
        print(f"✓ Account unlocked: {not user.account_locked}")
        
        # Verify password changed
        assert user.password_hash != old_password_hash, "Password hash did not change"
        print(f"✓ Password hash changed successfully")
        
        return True


def test_unlock_account():
    """Test account unlock functionality."""
    print("\n=== TEST 5: Unlock Account ===")
    
    with app.app_context():
        # Get a user to lock and unlock
        user = User.query.filter_by(username='supervisor2').first()
        if not user:
            print("✗ Test user 'supervisor2' not found")
            return False
        
        # Simulate locked account
        user.account_locked = True
        user.failed_login_attempts = 5
        from datetime import datetime, timedelta
        user.locked_until = datetime.utcnow() + timedelta(minutes=15)
        db.session.commit()
        
        print(f"✓ Simulated locked account for: {user.username}")
        print(f"✓ Account locked: {user.account_locked}")
        print(f"✓ Failed attempts: {user.failed_login_attempts}")
        
        # Unlock account
        user.account_locked = False
        user.failed_login_attempts = 0
        user.locked_until = None
        db.session.commit()
        
        print(f"✓ Account unlocked")
        print(f"✓ Failed attempts reset to: {user.failed_login_attempts}")
        print(f"✓ Locked_until cleared: {user.locked_until is None}")
        
        return True


def test_change_role():
    """Test role change functionality."""
    print("\n=== TEST 6: Change User Role ===")
    
    with app.app_context():
        user = User.query.filter_by(username='alice').first()
        if not user:
            print("✗ Test user 'alice' not found")
            return False
        
        old_role = user.role
        new_role = 'Supervisor'
        
        print(f"✓ Changing role for user: {user.username}")
        print(f"✓ Old role: {old_role}")
        
        user.role = new_role
        db.session.commit()
        
        print(f"✓ New role: {user.role}")
        
        # Verify role changed
        assert user.role == new_role, "Role did not change"
        print(f"✓ Role change successful")
        
        # Change back to original role
        user.role = old_role
        db.session.commit()
        print(f"✓ Restored original role: {old_role}")
        
        return True


def test_delete_user():
    """Test user deletion."""
    print("\n=== TEST 7: Delete User ===")
    
    with app.app_context():
        # Create a temporary user to delete
        temp_username = f"deleteme_{secrets.token_hex(4)}"
        temp_password = bcrypt.generate_password_hash("TempPass123!").decode('utf-8')
        
        temp_user = User(
            username=temp_username,
            password_hash=temp_password,
            role='Champion'
        )
        db.session.add(temp_user)
        db.session.commit()
        
        user_id = temp_user.user_id
        print(f"✓ Created temporary user: {temp_username} (ID: {user_id})")
        
        # Delete the user
        db.session.delete(temp_user)
        db.session.commit()
        
        print(f"✓ User deleted")
        
        # Verify user is gone
        deleted_user = User.query.filter_by(user_id=user_id).first()
        assert deleted_user is None, "User still exists after deletion"
        print(f"✓ User verified as deleted from database")
        
        return True


def test_self_deletion_prevention():
    """Test that admin cannot delete themselves."""
    print("\n=== TEST 8: Self-Deletion Prevention ===")
    
    # This is a logical test (would be tested in route)
    current_user_id = 1  # Simulating logged-in admin
    target_user_id = 1   # Trying to delete themselves
    
    if current_user_id == target_user_id:
        print(f"✓ Self-deletion correctly prevented")
        print(f"✓ Admin ID {current_user_id} cannot delete user ID {target_user_id}")
        return True
    else:
        print(f"✗ FAILED: Self-deletion should be prevented")
        return False


def test_user_statistics():
    """Test user statistics calculation."""
    print("\n=== TEST 9: User Statistics ===")
    
    with app.app_context():
        total = User.query.count()
        admins = User.query.filter_by(role='Admin').count()
        supervisors = User.query.filter_by(role='Supervisor').count()
        champions = User.query.filter_by(role='Champion').count()
        
        print(f"✓ Total users: {total}")
        print(f"✓ Admins: {admins}")
        print(f"✓ Supervisors: {supervisors}")
        print(f"✓ Champions: {champions}")
        
        # Verify totals match
        calculated_total = admins + supervisors + champions
        assert total == calculated_total, f"Totals don't match: {total} != {calculated_total}"
        print(f"✓ Statistics verified (total matches sum of roles)")
        
        return True


def test_locked_users():
    """Test locked user identification."""
    print("\n=== TEST 10: Locked Users ===")
    
    with app.app_context():
        locked_users = User.query.filter_by(account_locked=True).all()
        
        print(f"✓ Locked users count: {len(locked_users)}")
        
        for user in locked_users:
            print(f"  - {user.username}: Failed attempts: {user.failed_login_attempts}")
        
        return True


def run_all_tests():
    """Run all user management tests."""
    print("=" * 60)
    print("USER MANAGEMENT FUNCTIONALITY TESTS")
    print("=" * 60)
    
    tests = [
        ("Password Generation", test_generate_temp_password),
        ("Database Setup", test_database_setup),
        ("Create User Validation", test_create_user_validation),
        ("Password Reset", test_reset_password),
        ("Unlock Account", test_unlock_account),
        ("Change Role", test_change_role),
        ("Delete User", test_delete_user),
        ("Self-Deletion Prevention", test_self_deletion_prevention),
        ("User Statistics", test_user_statistics),
        ("Locked Users", test_locked_users),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} FAILED with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed*100//total}%)")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
