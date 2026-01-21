import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, UMVGlobalEntry
from services import umv_service


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


def test_create_umv_entry_success(app):
    with app.app_context():
        e = umv_service.create_umv_entry('site_name', 'Unda')
        assert getattr(e, 'entry_id', None) is not None
        assert e.key == 'site_name'


def test_create_umv_requires_key(app):
    with app.app_context():
        with pytest.raises(ValueError):
            umv_service.create_umv_entry('', 'value')


def test_update_umv_entry(app):
    with app.app_context():
        e = UMVGlobalEntry(key='k', value='v')
        db.session.add(e)
        db.session.commit()

        updated = umv_service.update_umv_entry(e.entry_id, 'k2', 'v2')
        assert updated.key == 'k2'
        assert updated.value == 'v2'


def test_delete_umv_entry(app):
    with app.app_context():
        e = UMVGlobalEntry(key='remove', value='x')
        db.session.add(e)
        db.session.commit()
        umv_service.delete_umv_entry(e.entry_id)
        assert db.session.get(UMVGlobalEntry, e.entry_id) is None
