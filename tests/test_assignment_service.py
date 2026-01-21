import os
import sys
import pytest
from datetime import date

# Ensure project root is on sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, User, Champion
from services import assignment_service


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


def create_supervisor(app, username='sup'):
    with app.app_context():
        sup = User(username=username, role='Supervisor')
        sup.set_password('secret')
        db.session.add(sup)
        db.session.commit()
        return sup.user_id, sup.username


def create_champion(app, supervisor_id=None, code='CHT', gender='Female'):
    with app.app_context():
        champ = Champion(full_name='Test Champ', gender=gender, phone_number='+1000000000', assigned_champion_code=code, supervisor_id=supervisor_id)
        db.session.add(champ)
        db.session.commit()
        return champ.champion_id


def test_assign_and_unassign_champion(app):
    sup_id, sup_name = create_supervisor(app, username='s1')
    champ_id = create_champion(app, code='CH1')

    with app.app_context():
        res = assignment_service.assign_champion(champ_id, sup_id)
        assert res['new_supervisor_name'] == sup_name

        refreshed = db.session.get(Champion, champ_id)
        assert refreshed.supervisor_id == sup_id

        res2 = assignment_service.unassign_champion(champ_id)
        refreshed = db.session.get(Champion, champ_id)
        assert refreshed.supervisor_id is None


def test_assign_invalid_supervisor_raises(app):
    with app.app_context():
        user = User(username='not_sup', role='Admin')
        user.set_password('secret')
        db.session.add(user)
        db.session.commit()

        champ_id = create_champion(app, code='CH2')

        with pytest.raises(ValueError):
            assignment_service.assign_champion(champ_id, user.user_id)


def test_assign_nonexistent_champion_raises(app):
    sup_id, _ = create_supervisor(app, username='s2')
    with app.app_context():
        with pytest.raises(ValueError):
            assignment_service.assign_champion(99999, sup_id)
