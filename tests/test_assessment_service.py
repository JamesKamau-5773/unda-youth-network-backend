import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, MentalHealthAssessment
from services import assessment_service


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


def test_create_assessment_success(app):
    data = {
        'champion_code': 'C123',
        'assessment_type': 'Initial',
        'risk_category': 'Low',
        'notes': 'All good'
    }
    with app.app_context():
        a = assessment_service.create_assessment(data, administered_by=1)
        assert a.assessment_id is not None
        assert a.champion_code == 'C123'


def test_create_assessment_requires_fields(app):
    data = {'champion_code': '', 'assessment_type': '', 'risk_category': ''}
    with app.app_context():
        with pytest.raises(ValueError):
            assessment_service.create_assessment(data, administered_by=1)


def test_delete_assessment(app):
    with app.app_context():
        a = MentalHealthAssessment(champion_code='X', assessment_type='T', risk_category='High')
        db.session.add(a)
        db.session.commit()
        assessment_service.delete_assessment(a.assessment_id)
        assert db.session.get(MentalHealthAssessment, a.assessment_id) is None
