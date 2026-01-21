import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, Podcast
from services import podcast_service


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


def test_create_podcast(app):
    data = {
        'title': 'Ep1',
        'description': 'First',
        'guest': 'Alice',
        'audio_url': 'http://audio/1.mp3',
        'thumbnail_url': None,
        'duration': '360',
        'episode_number': '1',
        'season_number': '1',
        'category': 'General',
        'tags': 'a,b,c',
        'published': True
    }
    with app.app_context():
        p = podcast_service.create_podcast(data, creator_id=1)
        assert p.podcast_id is not None
        assert p.title == 'Ep1'
        assert p.published is True


def test_update_podcast(app):
    with app.app_context():
        p = Podcast(title='Old', audio_url='http://audio/old.mp3', created_by=1)
        db.session.add(p)
        db.session.commit()

        data = {'title': 'New', 'description': 'Updated', 'tags': 'x,y'}
        updated = podcast_service.update_podcast(p.podcast_id, data)
        assert updated.title == 'New'
        assert updated.description == 'Updated'
        assert updated.tags == ['x', 'y']


def test_delete_podcast(app):
    with app.app_context():
        p = Podcast(title='ToDelete', audio_url='http://audio/todelete.mp3', created_by=1)
        db.session.add(p)
        db.session.commit()
        podcast_service.delete_podcast(p.podcast_id)
        assert db.session.get(Podcast, p.podcast_id) is None


def test_toggle_publish(app):
    with app.app_context():
        p = Podcast(title='Tog', audio_url='http://audio/tog.mp3', created_by=1)
        db.session.add(p)
        db.session.commit()
        podcast_service.toggle_publish_podcast(p.podcast_id)
        refreshed = db.session.get(Podcast, p.podcast_id)
        assert refreshed.published is True
        podcast_service.toggle_publish_podcast(p.podcast_id)
        refreshed = db.session.get(Podcast, p.podcast_id)
        assert refreshed.published is False
