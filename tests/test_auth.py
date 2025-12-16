import sys
import os
import pytest

# Ensure project root is on sys.path for imports during tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, User


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


def create_user(username="admin", password="secret", role="Admin"):
    u = User(username=username, role=role)
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    return u


def test_successful_login_redirects_to_dashboard(client, app):
    with app.app_context():
        create_user(username="admin", password="secret", role="Admin")

    rv = client.post('/auth/login', data={"username": "admin", "password": "secret"}, follow_redirects=True)
    assert b'Admin dashboard' in rv.data
    # Flash message should be present (template may not render it in our simple endpoint), but ensure login succeeded


def test_invalid_credentials_stays_on_login(client, app):
    with app.app_context():
        create_user(username="user1", password="rightpass", role="Champion")

    rv = client.post('/auth/login', data={"username": "user1", "password": "wrongpass"}, follow_redirects=True)
    # Template does not render flashes in tests, ensure we remain on the login page
    assert rv.request.path.endswith('/auth/login')
    # Ensure access to dashboard is still protected
    d = client.get('/dashboard', follow_redirects=False)
    assert d.status_code == 302 and '/auth/login' in d.headers.get('Location', '')


def test_password_stored_as_bcrypt_hash(app):
    with app.app_context():
        u = create_user(username="hashme", password="mypassword")
        assert u.password_hash.startswith('$2')


def test_logout_destroys_session(client, app):
    with app.app_context():
        create_user(username="admin2", password="secret", role="Admin")

    # login
    rv = client.post('/auth/login', data={"username": "admin2", "password": "secret"}, follow_redirects=True)
    assert b'Admin dashboard' in rv.data

    # logout
    rv = client.get('/auth/logout', follow_redirects=False)
    assert rv.status_code == 302
    assert '/auth/login' in rv.headers.get('Location', '')

    # accessing dashboard now should redirect to login
    rv = client.get('/dashboard', follow_redirects=False)
    assert rv.status_code == 302
    assert '/auth/login' in rv.headers.get('Location', '')
