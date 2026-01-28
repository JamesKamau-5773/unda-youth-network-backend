"""Email task with optional Celery integration.

This module provides `send_email_async`. If Celery is available the
function is registered as a Celery task; otherwise a synchronous
fallback is exposed so the application can run without Celery installed.
"""
import os
try:
    from .celery_app import make_celery
    from app import create_app
    app, _ = create_app()
    celery = make_celery(app)
except Exception:
    celery = None


def _send_email(to, subject, body):
    from email_utils import send_email
    return send_email(to=to, subject=subject, body=body)


if celery:
    @celery.task(name='tasks.send_email')
    def send_email_async(to, subject, body):
        try:
            return _send_email(to, subject, body)
        except Exception:
            # Allow Celery to handle retries/logging
            raise
else:
    # Fallback: call synchronously
    def send_email_async(to, subject, body):
        try:
            return _send_email(to, subject, body)
        except Exception:
            raise
