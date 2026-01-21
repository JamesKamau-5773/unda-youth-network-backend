from datetime import datetime, timezone
from typing import Tuple, List, Dict, Any
from sqlalchemy import func
from models import db, SeedFundingApplication


def list_applications(status_filter: str = 'all') -> Tuple[List[SeedFundingApplication], Dict[str, Any]]:
    q = db.session.query(SeedFundingApplication)
    if status_filter and status_filter != 'all':
        q = q.filter_by(status=status_filter)

    applications = q.order_by(SeedFundingApplication.submitted_at.desc()).all()

    total = db.session.query(func.count(SeedFundingApplication.application_id)).scalar() or 0
    pending = db.session.query(func.count(SeedFundingApplication.application_id)).filter(SeedFundingApplication.status == 'Pending').scalar() or 0
    under_review = db.session.query(func.count(SeedFundingApplication.application_id)).filter(SeedFundingApplication.status == 'Under Review').scalar() or 0
    approved = db.session.query(func.count(SeedFundingApplication.application_id)).filter(SeedFundingApplication.status == 'Approved').scalar() or 0
    rejected = db.session.query(func.count(SeedFundingApplication.application_id)).filter(SeedFundingApplication.status == 'Rejected').scalar() or 0
    funded = db.session.query(func.count(SeedFundingApplication.application_id)).filter(SeedFundingApplication.status == 'Funded').scalar() or 0

    total_requested = db.session.query(func.sum(SeedFundingApplication.total_budget_requested)).scalar() or 0
    total_approved = db.session.query(func.sum(SeedFundingApplication.approved_amount)).filter(SeedFundingApplication.status.in_(['Approved', 'Funded'])).scalar() or 0

    stats = {
        'total': int(total),
        'pending': int(pending),
        'under_review': int(under_review),
        'approved': int(approved),
        'rejected': int(rejected),
        'funded': int(funded),
        'total_requested': float(total_requested) if total_requested else 0,
        'total_approved': float(total_approved) if total_approved else 0,
    }

    return applications, stats


def get_application(application_id: int) -> SeedFundingApplication:
    app = db.session.get(SeedFundingApplication, application_id)
    if not app:
        raise ValueError('Application not found')
    return app


def approve_application(application_id: int, approved_amount: float, approval_conditions: str, admin_notes: str, reviewer_id: int) -> SeedFundingApplication:
    app = db.session.get(SeedFundingApplication, application_id)
    if not app:
        raise ValueError('Application not found')
    if approved_amount is None:
        raise ValueError('Approved amount is required')

    try:
        app.status = 'Approved'
        app.approved_amount = float(approved_amount)
        app.approval_conditions = approval_conditions if approval_conditions else None
        app.admin_notes = admin_notes if admin_notes else None
        app.reviewed_at = datetime.now(timezone.utc)
        app.reviewed_by = reviewer_id
        db.session.commit()
        return app
    except Exception:
        db.session.rollback()
        raise


def reject_application(application_id: int, rejection_reason: str, admin_notes: str, reviewer_id: int) -> SeedFundingApplication:
    app = db.session.get(SeedFundingApplication, application_id)
    if not app:
        raise ValueError('Application not found')
    if not rejection_reason:
        raise ValueError('Rejection reason is required')

    app.status = 'Rejected'
    app.rejection_reason = rejection_reason
    app.admin_notes = admin_notes if admin_notes else None
    app.reviewed_at = datetime.now(timezone.utc)
    app.reviewed_by = reviewer_id
    db.session.commit()
    return app


def mark_as_funded(application_id: int, disbursement_date, disbursement_method: str, disbursement_reference: str) -> SeedFundingApplication:
    app = db.session.get(SeedFundingApplication, application_id)
    if not app:
        raise ValueError('Application not found')
    if app.status != 'Approved':
        raise ValueError('Only approved applications can be marked as funded')

    try:
        if isinstance(disbursement_date, str):
            disbursement_date = datetime.strptime(disbursement_date, '%Y-%m-%d').date()

        app.status = 'Funded'
        app.disbursement_date = disbursement_date
        app.disbursement_method = disbursement_method
        app.disbursement_reference = disbursement_reference if disbursement_reference else None
        db.session.commit()
        return app
    except ValueError:
        raise
    except Exception:
        db.session.rollback()
        raise


def update_review_status(application_id: int, reviewer_id: int, admin_notes: str = None) -> SeedFundingApplication:
    app = db.session.get(SeedFundingApplication, application_id)
    if not app:
        raise ValueError('Application not found')

    app.status = 'Under Review'
    app.reviewed_at = datetime.now(timezone.utc)
    app.reviewed_by = reviewer_id
    if admin_notes:
        app.admin_notes = admin_notes
    db.session.commit()
    return app
