import io
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, MediaGallery, InstitutionalToolkitItem


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
def client(app):
    return app.test_client()


def create_admin_user(app):
    from models import User

    with app.app_context():
        admin = User(username="admin", role="Admin")
        admin.set_password("secret")
        db.session.add(admin)
        db.session.commit()
        return admin


def test_create_media_gallery_with_file(app, client):
    create_admin_user(app)
    # login
    client.post('/auth/login', data={"username": "admin", "password": "secret"})

    data = {
        'title': 'Test Gallery',
        'description': 'Integration upload test',
        'media_items': (io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 64), 'test.png')
    }

    rv = client.post('/admin/media-galleries/create', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert rv.status_code == 200

    with app.app_context():
        g = db.session.query(MediaGallery).first()
        assert g is not None
        assert g.title == 'Test Gallery'
        assert isinstance(g.media_items, list)
        # ensure the uploaded filename is recorded
        assert any(i.get('filename') == 'test.png' for i in (g.media_items or []))


def test_create_toolkit_item_with_attachment(app, client):
    create_admin_user(app)
    client.post('/auth/login', data={"username": "admin", "password": "secret"})

    data = {
        'title': 'Toolkit Guide',
        'content': 'Some guidance',
        'attachments': (io.BytesIO(b"PDFDATA"), 'guide.pdf')
    }

    rv = client.post('/admin/toolkit/create', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert rv.status_code == 200

    with app.app_context():
        it = db.session.query(InstitutionalToolkitItem).first()
        assert it is not None
        assert it.title == 'Toolkit Guide'
        assert isinstance(it.attachments, list)
        assert any(a.get('filename') == 'guide.pdf' for a in (it.attachments or []))
