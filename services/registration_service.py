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
from models import db, User, MemberRegistration


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

        db.session.commit()

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
