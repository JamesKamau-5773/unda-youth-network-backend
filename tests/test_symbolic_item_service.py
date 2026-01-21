import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, SymbolicItem
from services import symbolic_item_service


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


def test_create_symbolic_item_success(app):
    data = {
        'item_name': 'Badge',
        'item_type': 'Award',
        'description': 'A special badge',
        'total_quantity': 10
    }
    with app.app_context():
        item = symbolic_item_service.create_symbolic_item(data)
        assert item.item_id is not None
        assert item.item_name == 'Badge'


def test_create_symbolic_item_requires_name(app):
    data = {'item_type': 'Type'}
    with app.app_context():
        with pytest.raises(ValueError):
            symbolic_item_service.create_symbolic_item(data)


def test_update_symbolic_item(app):
    with app.app_context():
        s = SymbolicItem(item_name='Old', total_quantity=1)
        db.session.add(s)
        db.session.commit()

        data = {'item_name': 'New', 'total_quantity': 5}
        updated = symbolic_item_service.update_symbolic_item(s.item_id, data)
        assert updated.item_name == 'New'
        assert updated.total_quantity == 5


def test_delete_symbolic_item(app):
    with app.app_context():
        s = SymbolicItem(item_name='ToDelete')
        db.session.add(s)
        db.session.commit()
        symbolic_item_service.delete_symbolic_item(s.item_id)
        assert db.session.get(SymbolicItem, s.item_id) is None
