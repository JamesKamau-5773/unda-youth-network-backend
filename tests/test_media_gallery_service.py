import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, MediaGallery
from services import media_gallery_service


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


def test_create_media_gallery_success(app):
    data = {
        'title': 'Gallery 1',
        'description': 'Desc',
        'media_items': [{'url': 'https://img/1.jpg', 'type': 'image'}]
    }
    with app.app_context():
        g = media_gallery_service.create_media_gallery(data, creator_id=1)
        assert g.gallery_id is not None
        assert g.title == 'Gallery 1'


def test_create_media_gallery_requires_title(app):
    data = {'description': 'No title'}
    with app.app_context():
        with pytest.raises(ValueError):
            media_gallery_service.create_media_gallery(data, creator_id=1)


def test_update_media_gallery(app):
    with app.app_context():
        g = MediaGallery(title='Old', created_by=1)
        db.session.add(g)
        db.session.commit()

        data = {'title': 'New', 'description': 'Updated'}
        updated = media_gallery_service.update_media_gallery(g.gallery_id, data)
        assert updated.title == 'New'
        assert updated.description == 'Updated'


def test_delete_media_gallery(app):
    with app.app_context():
        g = MediaGallery(title='To delete', created_by=1)
        db.session.add(g)
        db.session.commit()
        media_gallery_service.delete_media_gallery(g.gallery_id)
        assert db.session.get(MediaGallery, g.gallery_id) is None
