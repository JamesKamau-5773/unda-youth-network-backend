import os
import sys
import pytest
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, Event
from services import event_service


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


def test_create_event_success(app):
    data = {
        'title': 'Debate Night',
        'motion': 'This house believes... ',
        'event_date': '2030-01-02T18:00',
        'registration_deadline': '2030-01-01T23:59',
        'max_participants': '100',
        'description': 'An exciting debate',
        'location': 'Main Hall',
        'organizer': 'Team',
        'status': 'Upcoming',
        'image_url': None,
    }
    with app.app_context():
        ev = event_service.create_event(data, creator_id=1)
        assert ev.event_id is not None
        assert ev.title == 'Debate Night'


def test_create_event_invalid_date(app):
    data = {
        'title': 'Bad Date',
        'motion': 'Motion',
        'event_date': 'not-a-date'
    }
    with app.app_context():
        with pytest.raises(ValueError):
            event_service.create_event(data, creator_id=1)


def test_update_event(app):
    with app.app_context():
        # create initial
        e = Event(title='X', motion='M', event_date=datetime.strptime('2030-01-02T18:00','%Y-%m-%dT%H:%M'), created_by=1)
        db.session.add(e)
        db.session.commit()
        data = {
            'title': 'Updated',
            'motion': 'New motion',
            'event_date': '2030-02-02T18:00',
            'max_participants': '50'
        }
        ev = event_service.update_event(e.event_id, data)
        assert ev.title == 'Updated'
        assert ev.max_participants == 50
