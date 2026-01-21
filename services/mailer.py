from typing import Any
from flask import current_app
from email_utils import send_invite_email, send_password_email


def send_invite(email: str, username: str, token: str, expires_at) -> bool:
    """Wrapper around the legacy email util to allow mocking in tests.

    Returns True if the underlying sender reports success, False otherwise.
    """
    try:
        return send_invite_email(email, username, token, expires_at)
    except Exception as e:
        current_app.logger.debug(f"mailer.send_invite failed: {e}")
        return False


def send_password(email: str, username: str, password: str) -> bool:
    try:
        return send_password_email(email, username, password)
    except Exception as e:
        current_app.logger.debug(f"mailer.send_password failed: {e}")
        return False
