import os
import sys
import pytest
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, User, ChampionApplication
from services import champion_application_service


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


def create_user(app, username='app_user'):
    with app.app_context():
        u = User(username=username, role=User.ROLE_PREVENTION_ADVOCATE)
        u.set_password('secret')
        db.session.add(u)
        db.session.commit()
        return u.user_id


def create_application(app, user_id, full_name='Applicant'):
    with app.app_context():
        a = ChampionApplication(user_id=user_id, full_name=full_name, phone_number='+1000000001', gender='Female', date_of_birth=date.today())
        db.session.add(a)
        db.session.commit()
        return a.application_id


def test_approve_application(app):
    reviewer_id = create_user(app, 'rev_app')
    user_id = create_user(app, 'applicant1')
    app_id = create_application(app, user_id, 'Applicant 1')

    with app.app_context():
        res = champion_application_service.approve_application(app_id, reviewer_id)
        application = res.get('application')
        assert application.status == 'Approved'
        assert application.reviewed_by == reviewer_id

        with pytest.raises(ValueError):
            champion_application_service.approve_application(app_id, reviewer_id)


def test_reject_application(app):
    reviewer_id = create_user(app, 'rev_app2')
    user_id = create_user(app, 'applicant2')
    app_id = create_application(app, user_id, 'Applicant 2')

    with app.app_context():
        res = champion_application_service.reject_application(app_id, reviewer_id, 'not a fit')
        application = res.get('application')
        assert application.status == 'Rejected'
        assert application.rejection_reason == 'not a fit'

        with pytest.raises(ValueError):
            champion_application_service.reject_application(app_id, reviewer_id, 'again')


def test_approve_nonexistent_raises(app):
    reviewer_id = create_user(app, 'rev_app3')
    with app.app_context():
        with pytest.raises(Exception):
            champion_application_service.approve_application(99999, reviewer_id)
