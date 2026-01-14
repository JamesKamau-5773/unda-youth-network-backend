#!/usr/bin/env python3
"""
Test email configuration and sending
"""
import os
import sys
import pytest
from app import create_app

# Create an app instance for this test module with TESTING enabled so
# initialization of networked services (Sentry) is skipped.
app, _ = create_app(test_config={
    'TESTING': True,
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    'WTF_CSRF_ENABLED': False
})
from email_utils import send_password_email

def test_email_config():
    """Test email configuration and attempt to send a test email"""
    with app.app_context():
        print("=" * 60)
        print("Email Configuration Test")
        print("=" * 60)
        
        # Check configuration
        print("\n📧 Email Configuration:")
        print(f"  MAIL_SERVER: {app.config.get('MAIL_SERVER')}")
        print(f"  MAIL_PORT: {app.config.get('MAIL_PORT')}")
        print(f"  MAIL_USE_TLS: {app.config.get('MAIL_USE_TLS')}")
        print(f"  MAIL_USERNAME: {app.config.get('MAIL_USERNAME')}")
        print(f"  MAIL_PASSWORD: {'*' * len(app.config.get('MAIL_PASSWORD', '')) if app.config.get('MAIL_PASSWORD') else 'NOT SET'}")
        print(f"  MAIL_DEFAULT_SENDER: {app.config.get('MAIL_DEFAULT_SENDER')}")
        
        # Check if all required fields are set
        missing = []
        if not app.config.get('MAIL_SERVER'):
            missing.append('MAIL_SERVER')
        if not app.config.get('MAIL_USERNAME'):
            missing.append('MAIL_USERNAME')
        if not app.config.get('MAIL_PASSWORD'):
            missing.append('MAIL_PASSWORD')

        if missing:
            pytest.skip(f"Missing email configuration: {', '.join(missing)}")

        print("\n✅ All email config variables are set")

        # If running under pytest / CI, skip interactive prompt
        if os.environ.get('PYTEST_CURRENT_TEST') or os.environ.get('CI') == 'true' or app.config.get('TESTING'):
            pytest.skip("Test email sending skipped in non-interactive test environment")
        # Ask for test email
        print("\n" + "=" * 60)
        test_email = input("Enter email address to send test to (or 'skip' to cancel): ").strip()
        
        if test_email.lower() == 'skip' or not test_email:
            pytest.skip("Test email sending skipped by user")
        
        print(f"\n📤 Sending test email to {test_email}...")
        
        try:
            result = send_password_email(
                recipient_email=test_email,
                username="test_user",
                temp_password="TestPass123!"
            )
            
            if result:
                print(f"\n✅ Email sent successfully to {test_email}")
                print("📬 Check your inbox (and spam folder)")
                assert result is True
            else:
                print(f"\n❌ Email sending failed - check logs above for details")
                assert False, "Email sending reported failure"
                
        except Exception as e:
            print(f"\n❌ Email sending error: {str(e)}")
            import traceback
            traceback.print_exc()
            assert False, f"Email sending raised exception: {str(e)}"

if __name__ == '__main__':
    try:
        test_email_config()
        print("=" * 60)
        sys.exit(0)
    except SystemExit:
        raise
    except Exception:
        # If any assertion fails or skip is raised, exit non-zero
        print("Test failed or skipped when run as script")
        sys.exit(1)
