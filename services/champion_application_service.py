from datetime import datetime, timezone
from flask import current_app
from models import db, ChampionApplication


def approve_application(application_id: int, reviewer_id: int) -> dict:
    application = db.session.get(ChampionApplication, application_id)
    if not application:
        raise ValueError('Application not found')

    if application.status != 'Pending':
        raise ValueError('Application has already been processed.')

    try:
        application.status = 'Approved'
        application.reviewed_at = datetime.now(timezone.utc)
        application.reviewed_by = reviewer_id

        db.session.commit()

        return {'application': application}
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error approving champion application')
        raise


def reject_application(application_id: int, reviewer_id: int, reason: str = 'No reason provided') -> dict:
    application = db.session.get(ChampionApplication, application_id)
    if not application:
        raise ValueError('Application not found')

    if application.status != 'Pending':
        raise ValueError('Application has already been processed.')

    try:
        application.status = 'Rejected'
        application.reviewed_at = datetime.now(timezone.utc)
        application.reviewed_by = reviewer_id
        application.rejection_reason = reason

        db.session.commit()

        return {'application': application}
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error rejecting champion application')
        raise
