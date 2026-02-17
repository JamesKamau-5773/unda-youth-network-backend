from datetime import datetime, timedelta, timezone
import secrets
from typing import Optional
from flask_bcrypt import Bcrypt
from flask import current_app
from models import db, User, Champion
from services.mailer import send_invite


def create_user(username: str, email: Optional[str], role: str) -> dict:
    """Create a new user, set an invite token and optionally send invite email.

    Returns a dict with keys: user, temp_password, invite_sent, invite_token, expires_at
    """
    bcrypt = Bcrypt()
    temp_password = secrets.token_urlsafe(8)

    new_user = User(
        username=username,
        email=email if email else None,
        role=role,
        password_hash=bcrypt.generate_password_hash(temp_password).decode('utf-8')
    )

    try:
        db.session.add(new_user)
        db.session.commit()

        invite_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        new_user.set_invite(invite_token, expires_at)

        invite_sent = False
        if email:
            try:
                invite_sent = send_invite(email, username, invite_token, expires_at)
            except Exception:
                current_app.logger.exception("Failed to send invite email")

        return {
            'user': new_user,
            'temp_password': temp_password,
            'invite_sent': invite_sent,
            'invite_token': invite_token,
            'expires_at': expires_at,
        }

    except Exception:
        db.session.rollback()
        raise


def reset_password(user_id: int) -> dict:
    """Reset password (admin-initiated) by creating an invite token and returning invite_url."""
    user = db.session.get(User, user_id)
    if not user:
        raise ValueError('User not found')

    bcrypt = Bcrypt()
    # Generate a temporary human-readable password and set it directly.
    temp_password = secrets.token_urlsafe(8)
    user.password_hash = bcrypt.generate_password_hash(temp_password).decode('utf-8')
    user.failed_login_attempts = 0
    # support both names used in codebases
    if hasattr(user, 'locked_until'):
        user.locked_until = None
    if hasattr(user, 'lockout_until'):
        user.lockout_until = None

    try:
        # Clear any existing invite tokens; admin prefers providing temp password.
        user.invite_token = None
        user.invite_token_expires = None

        db.session.commit()

        return {'user': user, 'temp_password': temp_password}

    except Exception:
        db.session.rollback()
        raise


def unlock_user(user_id: int) -> None:
    user = db.session.get(User, user_id)
    if not user:
        raise ValueError('User not found')
    user.failed_login_attempts = 0
    if hasattr(user, 'lockout_until'):
        user.lockout_until = None
    if hasattr(user, 'locked_until'):
        user.locked_until = None
    db.session.commit()


def change_role(user_id: int, new_role_raw: str) -> dict:
    user = db.session.get(User, user_id)
    if not user:
        raise ValueError('User not found')
    old_role = user.role
    try:
        user.set_role(new_role_raw)
        db.session.commit()
        return {'old_role': old_role, 'new_role': user.role}
    except ValueError:
        db.session.rollback()
        raise
    except Exception:
        db.session.rollback()
        raise


def delete_user(user_id: int, current_user_id: int) -> None:
    user = db.session.get(User, user_id)
    if not user:
        raise ValueError('User not found')
    if user.user_id == current_user_id:
        raise ValueError('Cannot delete own account')

    try:
        if getattr(user, 'champion_id', None):
            champion = db.session.get(Champion, user.champion_id)
            if champion:
                db.session.delete(champion)
        db.session.delete(user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def change_password(user_id: int, current_password: str, new_password: str) -> dict:
    """Validate and change a user's password.

    Raises ValueError with a user-friendly message on validation failure.
    Returns the updated user in a dict on success.
    """
    user = db.session.get(User, user_id)
    if not user:
        raise ValueError('User not found')
    bcrypt = Bcrypt()

    # Verify current password
    if not bcrypt.check_password_hash(user.password_hash, current_password):
        raise ValueError('Current password is incorrect')

    # Basic strength checks
    if len(new_password) < 8:
        raise ValueError('New password must be at least 8 characters long')

    has_upper = any(c.isupper() for c in new_password)
    has_lower = any(c.islower() for c in new_password)
    has_digit = any(c.isdigit() for c in new_password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in new_password)

    if not (has_upper and has_lower and has_digit and has_special):
        raise ValueError('Password must contain uppercase, lowercase, digit, and special character')

    # Don't allow same password
    if bcrypt.check_password_hash(user.password_hash, new_password):
        raise ValueError('New password must be different from current password')

    try:
        user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
        db.session.commit()
        return {'user': user}
    except Exception:
        db.session.rollback()
        raise
