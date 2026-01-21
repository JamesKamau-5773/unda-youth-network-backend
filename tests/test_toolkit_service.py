import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, InstitutionalToolkitItem
from services import toolkit_service


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


def test_create_toolkit_item_success(app):
    data = {'title': 'Guide', 'content': 'Use it', 'attachments': [{'url': 'a'}]}
    with app.app_context():
        item = toolkit_service.create_toolkit_item(data, creator_id=1)
        assert item.item_id is not None
        assert item.title == 'Guide'


def test_create_toolkit_requires_title(app):
    data = {'content': 'No title'}
    with app.app_context():
        with pytest.raises(ValueError):
            toolkit_service.create_toolkit_item(data, creator_id=1)


def test_update_toolkit_item(app):
    with app.app_context():
        it = InstitutionalToolkitItem(title='Old', created_by=1)
        db.session.add(it)
        db.session.commit()
        data = {'title': 'New', 'content': 'Updated'}
        updated = toolkit_service.update_toolkit_item(it.item_id, data)
        assert updated.title == 'New'
        assert updated.content == 'Updated'


def test_delete_toolkit_item(app):
    with app.app_context():
        it = InstitutionalToolkitItem(title='To delete', created_by=1)
        db.session.add(it)
        db.session.commit()
        toolkit_service.delete_toolkit_item(it.item_id)
        assert db.session.get(InstitutionalToolkitItem, it.item_id) is None
