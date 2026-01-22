from datetime import datetime, timezone
from models import db, MemberRegistration


def approve_registration(registration_id: int, reviewer_id: int):
    registration = db.session.get(MemberRegistration, registration_id)
    if not registration:
        raise ValueError('Registration not found')
    if registration.status != 'Pending':
        raise ValueError('Registration is not pending')

    registration.status = 'Approved'
    registration.reviewed_at = datetime.now(timezone.utc)
    registration.reviewed_by = reviewer_id

    db.session.commit()
    return {'registration': registration}


def reject_registration(registration_id: int, reviewer_id: int, reason: str = 'No reason provided'):
    registration = db.session.get(MemberRegistration, registration_id)
    if not registration:
        raise ValueError('Registration not found')
    if registration.status != 'Pending':
        raise ValueError('Registration is not pending')

    registration.status = 'Rejected'
    registration.reviewed_at = datetime.now(timezone.utc)
    registration.reviewed_by = reviewer_id
    registration.rejection_reason = reason

    db.session.commit()
    return {'registration': registration}
from datetime import datetime
from flask import current_app
from models import db, User, MemberRegistration, Certificate
import hmac
import hashlib


def _generate_certificate_pdf_bytes(user):
    """Generate a minimal PDF-like bytes blob for the certificate.

    This is a simple placeholder implementation; replace with real PDF
    generation (wkhtmltopdf / headless chrome / reportlab) in production.
    """
    content = f"Certificate of Membership\n\nName: {user.username}\nMember ID: {user.user_id}\nIssued: {datetime.utcnow().isoformat()}\n"
    # Minimal PDF wrapper: real PDF generation is recommended for production
    pdf = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n" + content.encode('utf-8') + b"\n%%EOF"
    return pdf


def _sign_certificate_bytes(secret_key: str, data: bytes) -> str:
    return hmac.new(secret_key.encode('utf-8'), data, hashlib.sha256).hexdigest()


def approve_registration(registration_id: int, reviewer_id: int) -> dict:
    registration = db.session.get(MemberRegistration, registration_id)
    if not registration:
        raise ValueError('Registration not found')

    if registration.status != 'Pending':
        raise ValueError('Registration has already been processed.')

    try:
        # Create user account from registration
        user = User(username=registration.username)
        user.set_role(User.ROLE_PREVENTION_ADVOCATE)
        user.password_hash = registration.password_hash

        db.session.add(user)
        db.session.flush()

        # Update registration metadata
        registration.status = 'Approved'
        registration.reviewed_at = datetime.now(timezone.utc)
        registration.reviewed_by = reviewer_id
        registration.created_user_id = user.user_id

        # After creating the user, generate an initial certificate
        try:
            pdf_bytes = _generate_certificate_pdf_bytes(user)
            secret = current_app.config.get('SECRET_KEY', 'dev-secret')
            signature = _sign_certificate_bytes(secret, pdf_bytes)

            cert = Certificate(user_id=user.user_id, pdf_data=pdf_bytes, signature=signature)
            db.session.add(cert)
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Failed to generate certificate')

        return {'user': user, 'registration': registration}

    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error approving registration')
        raise


def reject_registration(registration_id: int, reviewer_id: int, reason: str) -> dict:
    registration = db.session.get(MemberRegistration, registration_id)
    if not registration:
        raise ValueError('Registration not found')

    if registration.status != 'Pending':
        raise ValueError('Registration has already been processed.')

    try:
        registration.status = 'Rejected'
        registration.reviewed_at = datetime.now(timezone.utc)
        registration.reviewed_by = reviewer_id
        registration.rejection_reason = reason

        db.session.commit()

        return {'registration': registration}

    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error rejecting registration')
        raise
