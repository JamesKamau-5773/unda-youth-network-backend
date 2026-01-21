import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, ResourceItem
from services import resource_service


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


def test_create_resource_success(app):
    data = {'title': 'Resource 1', 'url': 'https://example.org', 'resource_type': 'Guide', 'tags': ['tag1']}
    with app.app_context():
        r = resource_service.create_resource_item(data, creator_id=1)
        assert r.resource_id is not None
        assert r.title == 'Resource 1'


def test_create_resource_requires_title(app):
    data = {'url': 'https://x'}
    with app.app_context():
        with pytest.raises(ValueError):
            resource_service.create_resource_item(data, creator_id=1)


def test_update_resource(app):
    with app.app_context():
        r = ResourceItem(title='Old', created_by=1)
        db.session.add(r)
        db.session.commit()
        data = {'title': 'New', 'description': 'Updated', 'tags': ['a','b']}
        updated = resource_service.update_resource_item(r.resource_id, data)
        assert updated.title == 'New'
        assert updated.tags == ['a','b']


def test_delete_resource(app):
    with app.app_context():
        r = ResourceItem(title='To delete', created_by=1)
        db.session.add(r)
        db.session.commit()
        resource_service.delete_resource_item(r.resource_id)
        assert db.session.get(ResourceItem, r.resource_id) is None
