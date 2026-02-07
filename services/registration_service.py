from datetime import datetime, timezone
from models import db, MemberRegistration, User, Champion, Certificate, generate_champion_code
from flask import current_app
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
    """Approve a member registration, create User and Champion profile"""
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
        user.email = registration.email
        user.date_of_birth = registration.date_of_birth
        user.gender = registration.gender or 'Other'
        user.county_sub_county = registration.county_sub_county

        db.session.add(user)
        db.session.flush()
        
        current_app.logger.info(f'Created user: {user.user_id} - {user.username}')
        
        # Generate unique champion code
        champion_code = generate_champion_code()
        current_app.logger.info(f'Generated champion code: {champion_code} for user: {user.username}')

        # Create Champion profile for Prevention Advocate
        champion = Champion(
            user_id=user.user_id,
            full_name=registration.full_name,
            email=registration.email,
            phone_number=registration.phone_number,
            date_of_birth=registration.date_of_birth,
            gender=registration.gender or 'Other',
            county_sub_county=registration.county_sub_county,
            assigned_champion_code=champion_code,
            champion_status='Active'
        )
        db.session.add(champion)
        db.session.flush()
        
        current_app.logger.info(f'Created champion: {champion.champion_id} for user: {user.user_id}')

        # Link user to champion
        user.champion_id = champion.champion_id

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
        except Exception:
            current_app.logger.exception('Failed to generate certificate')

        db.session.commit()
        return {'user': user, 'registration': registration, 'champion': champion}

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
