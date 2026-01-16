"""
Email utility for sending notifications
"""
from flask_mail import Mail, Message
from flask import current_app
import os

mail = Mail()

def init_mail(app):
    """Initialize Flask-Mail with app configuration"""
    mail.init_app(app)

def send_password_email(recipient_email, username, temp_password):
    """
    Send temporary password to user's email
    
    Args:
        recipient_email: User's email address
        username: Username for login
        temp_password: Temporary password
    
    Returns:
        True if sent successfully, False otherwise
    """
    # Compose email content
    subject = "Your UNDA Account Credentials"
    body = f"""
Hello,

Your account has been created on the UNDA Youth Network platform.

Login Credentials:
-------------------
Username: {username}
Temporary Password: {temp_password}

Login URL: {current_app.config.get('APP_URL', 'https://your-app-url.com')}/auth/login

IMPORTANT SECURITY NOTICE:
- You must change this password on your first login
- Do not share this password with anyone
- If you did not request this account, please contact the administrator immediately

Best regards,
UNDA Youth Network Team
"""

    html = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; background: #f9f9f9;">
        <div style="background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h2 style="color: #2c5aa0; margin-top: 0;">Welcome to UNDA Youth Network</h2>
            <p>Your account has been successfully created on the UNDA Youth Network platform.</p>
            <div style="background: #e7f3ff; border-left: 4px solid #2196F3; padding: 15px; margin: 20px 0; border-radius: 4px;">
                <h3 style="margin-top: 0; color: #0c5460;">Login Credentials</h3>
                <p style="margin: 5px 0;"><strong>Username:</strong> {username}</p>
                <p style="margin: 5px 0;"><strong>Temporary Password:</strong> <code style="background: #fff; padding: 4px 8px; border-radius: 3px; font-size: 16px; color: #d9534f;">{temp_password}</code></p>
            </div>
            <div style="margin: 20px 0;">
                <a href="{current_app.config.get('APP_URL', 'https://your-app-url.com')}/auth/login" style="display: inline-block; padding: 12px 30px; background: #2c5aa0; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">Login Now</a>
            </div>
            <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 4px;">
                <h4 style="margin-top: 0; color: #856404;">Security Notice</h4>
                <ul style="margin: 5px 0; padding-left: 20px; color: #856404;">
                    <li>You <strong>must change</strong> this password on your first login</li>
                    <li>Do not share this password with anyone</li>
                    <li>If you did not request this account, please contact the administrator immediately</li>
                </ul>
            </div>
            <p style="color: #666; font-size: 14px; margin-top: 30px;">Best regards,<br><strong>UNDA Youth Network Team</strong></p>
        </div>
        <p style="text-align: center; color: #666; font-size: 12px; margin-top: 20px;">This is an automated message. Please do not reply to this email.</p>
    </div>
</body>
</html>
"""

    # Respect global disable flag to avoid sending emails
    if current_app.config.get('DISABLE_EMAILS') or current_app.config.get('DISABLE_EMAIL_IN_BUILD'):
        current_app.logger.info(f"Email disabled by configuration; not sending password email to {recipient_email}")
        return False

    # Try to enqueue via Celery if available, otherwise send synchronously
    try:
        # Import inside function to avoid import-time circular dependencies
        from tasks.email_tasks import send_email_async
        # Use delay() to enqueue
        send_email_async.delay(recipient_email, subject, body)
        return True
    except Exception:
        # Fallback to synchronous send
        try:
            msg = Message(subject=subject, sender=current_app.config['MAIL_DEFAULT_SENDER'], recipients=[recipient_email])
            msg.body = body
            msg.html = html
            mail.send(msg)
            return True
        except Exception as e:
            current_app.logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
            return False

def send_email(to, subject, body, html=None):
    """Generic helper to send an email synchronously. """
    try:
        msg = Message(subject=subject, sender=current_app.config['MAIL_DEFAULT_SENDER'], recipients=[to])
        msg.body = body
        if html:
            msg.html = html
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send email to {to}: {str(e)}")
        return False


def send_invite_email(recipient_email, username, invite_token, expires_at=None):
    """Send a one-time invite/set-password link to an admin-created user.

    Args:
        recipient_email: recipient address
        username: username for the account
        invite_token: opaque token to include in URL
        expires_at: optional datetime object for expiry (used for message)

    Returns:
        True if email enqueued/sent, False otherwise
    """
    app_url = current_app.config.get('APP_URL', 'https://your-app-url.com')
    invite_url = f"{app_url}/auth/complete-invite?token={invite_token}"

    subject = 'UNDA: Account invite — set your password'
    expiry_text = ''
    if expires_at:
        try:
            expiry_text = f" This link expires on {expires_at.isoformat()} UTC."
        except Exception:
            expiry_text = ''

    body = f"Hello,\n\nAn administrator created an account for you on the UNDA Youth Network platform.\n\nUsername: {username}\n\nTo set your password and activate your account, please open the following secure link:{expiry_text}\n\n{invite_url}\n\nIf you did not expect this email, please contact your administrator immediately.\n\nBest regards,\nUNDA Youth Network Team\n"

    html = f"""
<html><body style='font-family: Arial, sans-serif;'>
  <div style='max-width:600px;margin:0 auto;padding:20px;background:#f9f9f9;'>
    <div style='background:#fff;padding:24px;border-radius:8px;'>
      <h2 style='color:#2c5aa0'>You're invited to UNDA</h2>
      <p>An administrator created an account for you. Click the button below to set your password and sign in.</p>
      <p style='text-align:center;margin:24px 0;'>
        <a href='{invite_url}' style='display:inline-block;padding:12px 20px;background:#2c5aa0;color:#fff;border-radius:6px;text-decoration:none;font-weight:600;'>Set your password</a>
      </p>
      <p style='color:#666;font-size:0.9rem;'>If the button doesn't work, copy and paste this link into your browser:<br/>{invite_url}</p>
      <p style='color:#666;font-size:0.85rem;margin-top:20px;'>If you did not expect this, contact your administrator.</p>
    </div>
  </div>
</body></html>
"""

    # Respect global disable flag to avoid sending emails
    if current_app.config.get('DISABLE_EMAILS') or current_app.config.get('DISABLE_EMAIL_IN_BUILD'):
        current_app.logger.info(f"Email disabled by configuration; not sending invite email to {recipient_email}")
        return False

    # Try async enqueue first
    try:
        from tasks.email_tasks import send_email_async
        send_email_async.delay(recipient_email, subject, body)
        return True
    except Exception:
        return send_email(recipient_email, subject, body, html)
