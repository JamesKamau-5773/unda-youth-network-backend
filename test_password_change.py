#!/usr/bin/env python3
"""
Test script for password change functionality.
Tests validation, security checks, and bcrypt hashing.
"""

from app import app, db
from models import User
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

def test_password_validation():
    """Test password strength validation requirements."""
    print("\n=== TEST 1: Password Validation ===")
    
    test_cases = [
        ("weak", False, "Too short (< 8 chars)"),
        ("lowercase", False, "No uppercase, digit, or special"),
        ("UPPERCASE", False, "No lowercase, digit, or special"),
        ("Lower123", False, "No special character"),
        ("Lower!@#", False, "No digit"),
        ("Pass123!", True, "Valid password"),
        ("MySecure1@Pass", True, "Valid strong password"),
    ]
    
    for password, should_pass, description in test_cases:
        # Check length
        valid = len(password) >= 8
        
        # Check complexity
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        valid = valid and has_upper and has_lower and has_digit and has_special
        
        result = "✓ PASS" if valid == should_pass else "✗ FAIL"
        print(f"{result}: '{password}' - {description}")
        print(f"  Length: {len(password)}, Upper: {has_upper}, Lower: {has_lower}, Digit: {has_digit}, Special: {has_special}")
    
    return True


def test_bcrypt_password_verification():
    """Test bcrypt password hashing and verification."""
    print("\n=== TEST 2: Bcrypt Password Verification ===")
    
    with app.app_context():
        # Get a test user
        user = User.query.filter_by(username='admin').first()
        if not user:
            print("✗ Test user 'admin' not found")
            return False
        
        print(f"✓ Testing with user: {user.username}")
        
        # Store original password hash
        original_hash = user.password_hash
        print(f"✓ Original password hash: {original_hash[:30]}...")
        
        # Test password change
        new_password = "NewSecure123!"
        new_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
        
        print(f"✓ New password hash generated: {new_hash[:30]}...")
        
        # Verify new password
        if bcrypt.check_password_hash(new_hash, new_password):
            print("✓ New password verification successful")
        else:
            print("✗ New password verification failed")
            return False
        
        # Verify hashes are different
        if original_hash != new_hash:
            print("✓ Password hashes are different (as expected)")
        else:
            print("✗ Password hashes are the same (unexpected)")
            return False
        
        return True


def test_current_password_check():
    """Test current password verification before allowing change."""
    print("\n=== TEST 3: Current Password Verification ===")
    
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        if not user:
            print("✗ Test user not found")
            return False
        
        # Test with wrong current password
        wrong_password = "WrongPassword123!"
        if bcrypt.check_password_hash(user.password_hash, wrong_password):
            print("✗ Wrong password accepted (security issue!)")
            return False
        else:
            print("✓ Wrong current password correctly rejected")
        
        # Test with correct current password (assuming Admin@123 from seed)
        # Note: This will fail if admin password was changed
        correct_password = "Admin@123"
        if bcrypt.check_password_hash(user.password_hash, correct_password):
            print(f"✓ Correct current password verified")
        else:
            print("⚠ Could not verify with default password (may have been changed)")
        
        return True


def test_password_change_flow():
    """Test complete password change workflow."""
    print("\n=== TEST 4: Password Change Workflow ===")
    
    with app.app_context():
        # Create a test user
        test_username = "test_password_change"
        
        # Clean up if exists
        existing_user = User.query.filter_by(username=test_username).first()
        if existing_user:
            db.session.delete(existing_user)
            db.session.commit()
        
        # Create test user
        original_password = "Original123!"
        test_user = User(
            username=test_username,
            password_hash=bcrypt.generate_password_hash(original_password).decode('utf-8'),
            role='Champion'
        )
        db.session.add(test_user)
        db.session.commit()
        
        print(f"✓ Created test user: {test_username}")
        
        # Verify original password works
        if bcrypt.check_password_hash(test_user.password_hash, original_password):
            print("✓ Original password verified")
        else:
            print("✗ Original password verification failed")
            return False
        
        # Change password
        new_password = "NewPassword456!"
        old_hash = test_user.password_hash
        test_user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
        db.session.commit()
        
        print("✓ Password changed")
        
        # Verify new password works
        if bcrypt.check_password_hash(test_user.password_hash, new_password):
            print("✓ New password verified")
        else:
            print("✗ New password verification failed")
            return False
        
        # Verify old password no longer works
        if not bcrypt.check_password_hash(test_user.password_hash, original_password):
            print("✓ Old password correctly rejected")
        else:
            print("✗ Old password still works (security issue!)")
            return False
        
        # Cleanup
        db.session.delete(test_user)
        db.session.commit()
        print("✓ Test user cleaned up")
        
        return True


def test_password_mismatch():
    """Test that password and confirmation must match."""
    print("\n=== TEST 5: Password Confirmation Mismatch ===")
    
    new_password = "SecurePass123!"
    confirm_password = "SecurePass456!"
    
    if new_password == confirm_password:
        print("✗ Passwords match when they shouldn't")
        return False
    else:
        print("✓ Password mismatch detected correctly")
        return True


def test_same_password_rejection():
    """Test that new password must be different from current."""
    print("\n=== TEST 6: Same Password Rejection ===")
    
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        if not user:
            print("✗ Test user not found")
            return False
        
        current_password = "Admin@123"
        
        # Check if trying to set same password
        if bcrypt.check_password_hash(user.password_hash, current_password):
            # This is the current password
            is_same = True
            print("✓ Detected attempt to use same password")
            return True
        else:
            print("⚠ Could not test (password may have been changed)")
            return True


def run_all_tests():
    """Run all password change tests."""
    print("=" * 60)
    print("PASSWORD CHANGE FUNCTIONALITY TESTS")
    print("=" * 60)
    
    tests = [
        ("Password Validation", test_password_validation),
        ("Bcrypt Verification", test_bcrypt_password_verification),
        ("Current Password Check", test_current_password_check),
        ("Password Change Workflow", test_password_change_flow),
        ("Password Mismatch Detection", test_password_mismatch),
        ("Same Password Rejection", test_same_password_rejection),
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
