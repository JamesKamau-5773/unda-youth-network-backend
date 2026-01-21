import os
import sys
from decimal import Decimal
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, SeedFundingApplication, User
from services import seed_funding_service


@pytest.fixture
def app():
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "RATELIMIT_STORAGE_URL": "memory://",
    }
    app, limiter = create_app(test_config=test_config)

    with app.app_context():
        db.create_all()
        yield app


@pytest.fixture
def admin_user(app):
    with app.app_context():
        u = User(username='admin', role='Admin')
        u.set_password('secret')
        db.session.add(u)
        db.session.commit()
        return u.user_id


def _create_application(app, **kwargs):
    with app.app_context():
        a = SeedFundingApplication(
            applicant_name=kwargs.get('applicant_name', 'Test'),
            phone_number=kwargs.get('phone_number', '0700000000'),
            project_title=kwargs.get('project_title', 'Proj'),
            project_description=kwargs.get('project_description', 'Desc'),
            total_budget_requested=Decimal(kwargs.get('total_budget_requested', '1000.00')),
            **{k: v for k, v in kwargs.items() if k not in ['applicant_name','phone_number','project_title','project_description','total_budget_requested']}
        )
        db.session.add(a)
        db.session.commit()
        return a.application_id


def test_list_applications_and_stats(app):
    a1_id = _create_application(app, total_budget_requested='1000.00', status='Approved', approved_amount=Decimal('800.00'))
    a2_id = _create_application(app, total_budget_requested='2000.00', status='Funded', approved_amount=Decimal('1500.00'))

    applications, stats = seed_funding_service.list_applications()
    assert isinstance(applications, list)
    assert stats['total'] >= 2
    assert stats['total_requested'] >= 3000
    assert stats['total_approved'] >= 2300


def test_approve_application_sets_fields(app, admin_user):
    a_id = _create_application(app, total_budget_requested='5000.00')
    with app.app_context():
        seed_funding_service.approve_application(a_id, 2500.00, 'Condition', 'Notes', admin_user)
        updated = db.session.get(SeedFundingApplication, a_id)
        assert updated.status == 'Approved'
        assert float(updated.approved_amount) == 2500.00
        assert updated.reviewed_by == admin_user


def test_reject_application_requires_reason(app, admin_user):
    a_id = _create_application(app)
    with app.app_context():
        with pytest.raises(ValueError):
            seed_funding_service.reject_application(a_id, '', '', admin_user)


def test_mark_as_funded_requires_approved(app, admin_user):
    a_id = _create_application(app)
    with app.app_context():
        # Not approved yet
        with pytest.raises(ValueError):
            seed_funding_service.mark_as_funded(a_id, '2025-01-01', 'MPesa', 'REF123')
        # Approve then mark as funded
        seed_funding_service.approve_application(a_id, 1000.00, '', '', admin_user)
        funded = seed_funding_service.mark_as_funded(a_id, '2025-01-01', 'MPesa', 'REF123')
        assert funded.status == 'Funded'
        assert str(funded.disbursement_date).startswith('2025')


def test_update_review_status_sets_under_review(app, admin_user):
    a_id = _create_application(app)
    with app.app_context():
        seed_funding_service.update_review_status(a_id, admin_user, 'note')
        updated = db.session.get(SeedFundingApplication, a_id)
        assert updated.status == 'Under Review'
        assert updated.reviewed_by == admin_user
