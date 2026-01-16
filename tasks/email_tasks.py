from .celery_app import make_celery
from app import create_app
import os

app, _ = create_app()
celery = make_celery(app)


@celery.task(name='tasks.send_email')
def send_email_async(to, subject, body):
    # Import inside task to avoid import-time side effects
    from email_utils import send_email
    try:
        send_email(to=to, subject=subject, body=body)
    except Exception:
        # Let Celery handle retries/logging
        raise
