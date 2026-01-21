import os
import sys
import pytest
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, User, MemberRegistration
from services import registration_service


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


def create_reviewer(app, username='rev'):
    with app.app_context():
        u = User(username=username, role=User.ROLE_ADMIN)
        u.set_password('secret')
        db.session.add(u)
        db.session.commit()
        return u.user_id


def create_registration(app, username='reg1'):
    with app.app_context():
        r = MemberRegistration(full_name='Reg One', username=username, phone_number='+1000000000')
        r.set_password('secret')
        db.session.add(r)
        db.session.commit()
        return r.registration_id


def test_approve_registration_creates_user(app):
    reviewer_id = create_reviewer(app, 'admin1')
    reg_id = create_registration(app, 'new_user')

    with app.app_context():
        res = registration_service.approve_registration(reg_id, reviewer_id)
        user = res.get('user')
        registration = res.get('registration')

        assert user is not None
        assert user.username == 'new_user'
        assert user.role == User.ROLE_PREVENTION_ADVOCATE
        assert registration.status == 'Approved'
        assert registration.created_user_id == user.user_id

        # Approving again should raise
        with pytest.raises(ValueError):
            registration_service.approve_registration(reg_id, reviewer_id)


def test_reject_registration_marks_rejected(app):
    reviewer_id = create_reviewer(app, 'admin2')
    reg_id = create_registration(app, 'reject_me')

    with app.app_context():
        res = registration_service.reject_registration(reg_id, reviewer_id, 'invalid')
        registration = res.get('registration')
        assert registration.status == 'Rejected'
        assert registration.rejection_reason == 'invalid'

        # Rejecting again should raise
        with pytest.raises(ValueError):
            registration_service.reject_registration(reg_id, reviewer_id, 'again')
