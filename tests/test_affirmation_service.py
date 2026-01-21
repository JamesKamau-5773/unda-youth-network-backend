import os
import sys
import pytest
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, DailyAffirmation
from services import affirmation_service


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


def test_create_affirmation_success(app):
    data = {
        'content': 'Be kind to yourself',
        'theme': 'Self Care',
        'scheduled_date': '2030-01-01'
    }
    with app.app_context():
        a = affirmation_service.create_affirmation(data, creator_id=1)
        assert a.affirmation_id is not None
        assert a.content == 'Be kind to yourself'


def test_create_affirmation_requires_content(app):
    data = {'theme': 'No Content'}
    with app.app_context():
        with pytest.raises(ValueError):
            affirmation_service.create_affirmation(data, creator_id=1)


def test_update_affirmation(app):
    with app.app_context():
        a = DailyAffirmation(content='Old', theme='T', created_by=1)
        db.session.add(a)
        db.session.commit()

        data = {'content': 'Updated', 'theme': 'New'}
        updated = affirmation_service.update_affirmation(a.affirmation_id, data)
        assert updated.content == 'Updated'
        assert updated.theme == 'New'


def test_delete_affirmation(app):
    with app.app_context():
        a = DailyAffirmation(content='To delete', created_by=1)
        db.session.add(a)
        db.session.commit()
        affirmation_service.delete_affirmation(a.affirmation_id)
        assert db.session.get(DailyAffirmation, a.affirmation_id) is None
