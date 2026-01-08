#!/usr/bin/env python3
"""
Test email configuration and sending
"""
from app import app
from email_utils import send_password_email
import sys

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
            print(f"\n❌ Missing configuration: {', '.join(missing)}")
            return False
        
        print("\n✅ All email config variables are set")
        
        # Ask for test email
        print("\n" + "=" * 60)
        test_email = input("Enter email address to send test to (or 'skip' to cancel): ").strip()
        
        if test_email.lower() == 'skip' or not test_email:
            print("Test email sending skipped")
            return True
        
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
                return True
            else:
                print(f"\n❌ Email sending failed - check logs above for details")
                return False
                
        except Exception as e:
            print(f"\n❌ Email sending error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = test_email_config()
    print("=" * 60)
    sys.exit(0 if success else 1)
