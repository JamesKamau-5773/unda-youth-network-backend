import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, User
from services import user_service
from flask_bcrypt import Bcrypt


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


def create_user(app, username='u1'):
    with app.app_context():
        u = User(username=username, role=User.ROLE_PREVENTION_ADVOCATE)
        u.set_password('OldPass1!')
        db.session.add(u)
        db.session.commit()
        return u.user_id


def test_change_password_success(app):
    user_id = create_user(app, 'changeme')
    with app.app_context():
        res = user_service.change_password(user_id, 'OldPass1!', 'NewPass2%')
        user = res.get('user')
        assert user is not None
        # verify new password works
        bcrypt = Bcrypt()
        assert bcrypt.check_password_hash(user.password_hash, 'NewPass2%')


def test_change_password_invalid_current(app):
    user_id = create_user(app, 'badcurrent')
    with app.app_context():
        with pytest.raises(ValueError):
            user_service.change_password(user_id, 'WrongOld!', 'Another1$')


def test_change_password_weak(app):
    user_id = create_user(app, 'weakpass')
    with app.app_context():
        with pytest.raises(ValueError):
            user_service.change_password(user_id, 'OldPass1!', 'short')


def test_change_password_same_as_old(app):
    user_id = create_user(app, 'samepass')
    with app.app_context():
        with pytest.raises(ValueError):
            user_service.change_password(user_id, 'OldPass1!', 'OldPass1!')
