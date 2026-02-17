# Email Notification Setup Guide

## Overview
The system now supports sending temporary passwords via email when creating new users.

## Setup Steps

### 1. Install Flask-Mail
```bash
source .venv/bin/activate
pip install Flask-Mail==0.10.0
```

### 2. Create Database Migration
Add email field to User model:
```bash
flask db migrate -m "add_email_to_user_model"
flask db upgrade
```

### 3. Configure Email Service

#### Option A: Gmail (for development/testing)
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Step Verification
3. Go to [App Passwords](https://myaccount.google.com/apppasswords)
4. Generate a password for "Mail" app
5. Add to your `.env` file:

```bash
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-16-char-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com
APP_URL=http://127.0.0.1:5000
```

#### Option B: SendGrid (recommended for production)
1. Sign up at [SendGrid](https://sendgrid.com/)
2. Create an API key
3. Add to `.env`:

```bash
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=apikey
MAIL_PASSWORD=your-sendgrid-api-key
MAIL_DEFAULT_SENDER=noreply@unda.org
APP_URL=https://your-production-url.com
```

#### Option C: Mailgun
```bash
MAIL_SERVER=smtp.mailgun.org
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=postmaster@your-domain.mailgun.org
MAIL_PASSWORD=your-mailgun-smtp-password
MAIL_DEFAULT_SENDER=noreply@unda.org
```

### 4. Test Email Sending
Create a test user with an email address through the admin dashboard.

## How It Works

1. **Admin creates user** with optional email field
2. **Password generated** - secure random password created
3. **Email sent** (if email provided) - formatted HTML email with:
   - Username and password
   - Login link
   - Security warnings
4. **Success page** shows:
   - Email sent confirmation (green banner)
   - Password display (for manual copying if needed)
   - Copy to clipboard button

## Features

- **Optional email** - Email field is not required
- **Dual delivery** - Shows password on screen AND emails it
- **Email status** - Clear feedback if email fails
- **Beautiful HTML email** - Professional formatted email
- **Fallback handling** - If email fails, admin can still copy password
- **Security warnings** - Email includes password change reminders

## Troubleshooting

### Gmail "Less Secure Apps" Error
- Use App Passwords (not your regular Gmail password)
- Requires 2-Step Verification enabled

### SendGrid Not Sending
- Verify API key is valid
- Check domain authentication
- Review SendGrid activity logs

### Email Not Received
1. Check spam/junk folder
2. Verify email address is correct
3. Check server logs for errors: `tail -f server.log`
4. Test SMTP connection:
```python
from flask import Flask
from email_utils import mail, send_password_email
app = Flask(__name__)
# ... configure app ...
with app.app_context():
    send_password_email('test@example.com', 'testuser', 'TestPass123!')
```

## Security Best Practices

1. **Never commit credentials** - Keep `.env` in `.gitignore`
2. **Use app passwords** - Don't use your main email password
3. **Use dedicated sender** - Create noreply@yourdomain.com
4. **Production email service** - Use SendGrid/Mailgun for production
5. **Monitor email logs** - Track delivery success/failures
