"""
Support Review Service
Handles business logic for partnership inquiries, volunteer submissions, and host submissions.
"""
from models import db, PartnershipInquiry, VolunteerSubmission, HostSubmission
from datetime import datetime, timezone


# ─── Partnership Inquiries ─────────────────────────────────────────────────────

def create_partnership_inquiry(data):
    """Create a new partnership inquiry from frontend form data."""
    inquiry = PartnershipInquiry(
        organization_name=data['organizationName'].strip(),
        contact_person=data['contactPerson'].strip(),
        email=data['email'].strip().lower(),
        partnership_type=data['partnershipType'].strip(),
        message=data['message'].strip(),
    )
    db.session.add(inquiry)
    db.session.commit()
    return inquiry


def list_partnership_inquiries(status_filter='all'):
    """List partnership inquiries with optional status filter."""
    try:
        query = PartnershipInquiry.query.order_by(PartnershipInquiry.submitted_at.desc())
        if status_filter and status_filter != 'all':
            query = query.filter_by(status=status_filter)

        inquiries = query.all()
        stats = {
            'total': PartnershipInquiry.query.count(),
            'pending': PartnershipInquiry.query.filter_by(status='Pending').count(),
            'under_review': PartnershipInquiry.query.filter_by(status='Under Review').count(),
            'approved': PartnershipInquiry.query.filter_by(status='Approved').count(),
            'rejected': PartnershipInquiry.query.filter_by(status='Rejected').count(),
        }
        return inquiries, stats
    except Exception:
        # Table may not exist yet; return empty results
        return [], {
            'total': 0,
            'pending': 0,
            'under_review': 0,
            'approved': 0,
            'rejected': 0,
        }


def get_partnership_inquiry(inquiry_id):
    """Get a single partnership inquiry by ID."""
    inquiry = db.session.get(PartnershipInquiry, inquiry_id)
    if not inquiry:
        raise ValueError('Partnership inquiry not found')
    return inquiry


def update_partnership_inquiry_status(inquiry_id, status, admin_notes, reviewer_id):
    """Update the status of a partnership inquiry."""
    inquiry = get_partnership_inquiry(inquiry_id)
    inquiry.status = status
    inquiry.admin_notes = admin_notes or inquiry.admin_notes
    inquiry.reviewed_at = datetime.now(timezone.utc)
    inquiry.reviewed_by = reviewer_id
    db.session.commit()
    return inquiry


# ─── Volunteer Submissions ─────────────────────────────────────────────────────

def create_volunteer_submission(data):
    """Create a new volunteer submission from frontend form data."""
    submission = VolunteerSubmission(
        full_name=data['name'].strip(),
        email=data['email'].strip().lower(),
        phone=data.get('phone', '').strip() or None,
        interest=data['interest'].strip(),
        motivation=data.get('motivation', '').strip() or None,
    )
    db.session.add(submission)
    db.session.commit()
    return submission


def list_volunteer_submissions(status_filter='all'):
    """List volunteer submissions with optional status filter."""
    try:
        query = VolunteerSubmission.query.order_by(VolunteerSubmission.submitted_at.desc())
        if status_filter and status_filter != 'all':
            query = query.filter_by(status=status_filter)

        submissions = query.all()
        stats = {
            'total': VolunteerSubmission.query.count(),
            'pending': VolunteerSubmission.query.filter_by(status='Pending').count(),
            'under_review': VolunteerSubmission.query.filter_by(status='Under Review').count(),
            'approved': VolunteerSubmission.query.filter_by(status='Approved').count(),
            'rejected': VolunteerSubmission.query.filter_by(status='Rejected').count(),
        }
        return submissions, stats
    except Exception:
        # Table may not exist yet; return empty results
        return [], {
            'total': 0,
            'pending': 0,
            'under_review': 0,
            'approved': 0,
            'rejected': 0,
        }


def get_volunteer_submission(submission_id):
    """Get a single volunteer submission by ID."""
    submission = db.session.get(VolunteerSubmission, submission_id)
    if not submission:
        raise ValueError('Volunteer submission not found')
    return submission


def update_volunteer_submission_status(submission_id, status, admin_notes, reviewer_id):
    """Update the status of a volunteer submission."""
    submission = get_volunteer_submission(submission_id)
    submission.status = status
    submission.admin_notes = admin_notes or submission.admin_notes
    submission.reviewed_at = datetime.now(timezone.utc)
    submission.reviewed_by = reviewer_id
    db.session.commit()
    return submission


# ─── Host Submissions ──────────────────────────────────────────────────────────

def create_host_submission(data):
    """Create a new host event submission from frontend form data."""
    submission = HostSubmission(
        full_name=data['name'].strip(),
        email=data['email'].strip().lower(),
        phone=data.get('phone', '').strip() or None,
        event_type=data['interest'].strip(),
        event_description=data.get('motivation', '').strip() or None,
    )
    db.session.add(submission)
    db.session.commit()
    return submission


def list_host_submissions(status_filter='all'):
    """List host submissions with optional status filter."""
    try:
        query = HostSubmission.query.order_by(HostSubmission.submitted_at.desc())
        if status_filter and status_filter != 'all':
            query = query.filter_by(status=status_filter)

        submissions = query.all()
        stats = {
            'total': HostSubmission.query.count(),
            'pending': HostSubmission.query.filter_by(status='Pending').count(),
            'under_review': HostSubmission.query.filter_by(status='Under Review').count(),
            'approved': HostSubmission.query.filter_by(status='Approved').count(),
            'rejected': HostSubmission.query.filter_by(status='Rejected').count(),
        }
        return submissions, stats
    except Exception:
        # Table may not exist yet; return empty results
        return [], {
            'total': 0,
            'pending': 0,
            'under_review': 0,
            'approved': 0,
            'rejected': 0,
        }


def get_host_submission(submission_id):
    """Get a single host submission by ID."""
    submission = db.session.get(HostSubmission, submission_id)
    if not submission:
        raise ValueError('Host submission not found')
    return submission


def update_host_submission_status(submission_id, status, admin_notes, reviewer_id):
    """Update the status of a host event submission."""
    submission = get_host_submission(submission_id)
    submission.status = status
    submission.admin_notes = admin_notes or submission.admin_notes
    submission.reviewed_at = datetime.now(timezone.utc)
    submission.reviewed_by = reviewer_id
    db.session.commit()
    return submission
