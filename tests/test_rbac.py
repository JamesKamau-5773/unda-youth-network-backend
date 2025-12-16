import sys
import os
import pytest

# Ensure project root is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, User


def create_user(username="user", password="secret", role="Champion"):
    u = User(username=username, role=role)
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    return u


def login_client(client, username, password):
    return client.post('/auth/login', data={"username": username, "password": password}, follow_redirects=True)


@pytest.fixture
def app():
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    }
    app, limiter = create_app(test_config=test_config)
    with app.app_context():
        db.create_all()
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_admin_access_register(client, app):
    with app.app_context():
        create_user(username="admin", password="secret", role="Admin")

    login_client(client, "admin", "secret")
    rv = client.get('/auth/register', follow_redirects=True)
    assert rv.status_code == 200
    assert b'Registration form' in rv.data


def test_champion_cannot_access_register(client, app):
    with app.app_context():
        create_user(username="champ", password="secret", role="Champion")

    login_client(client, "champ", "secret")
    rv = client.get('/auth/register', follow_redirects=True)
    # Should be redirected to their dashboard
    assert b'Champion dashboard' in rv.data


def test_unauthenticated_access_dashboard_redirects_to_login(client):
    rv = client.get('/dashboard', follow_redirects=False)
    assert rv.status_code == 302
    assert '/auth/login' in rv.headers.get('Location', '')


def test_supervisor_cannot_access_admin_settings(client, app):
    with app.app_context():
        create_user(username="sup", password="secret", role="Supervisor")

    login_client(client, "sup", "secret")
    rv = client.get('/admin/settings', follow_redirects=True)
    # Should end up on supervisor dashboard due to access denied redirect
    assert b'Supervisor dashboard' in rv.data
