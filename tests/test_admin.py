from models import db, User
from datetime import datetime


def make_admin(app, username='admin', password='secret'):
    with app.app_context():
        u = User(username=username, email=f"{username}@example.com")
        u.set_password(password)
        u.set_role(User.ROLE_ADMIN)
        db.session.add(u)
        db.session.commit()
        return u


def test_admin_requires_login(client):
    resp = client.get('/admin/users', follow_redirects=False)
    assert resp.status_code in (302, 401, 302)


def test_admin_pages_accessible_after_login(client, app):
    # create admin
    make_admin(app, username='site_admin', password='pw123')

    # login via API
    resp = client.post('/api/auth/login', json={'username': 'site_admin', 'password': 'pw123'})
    assert resp.status_code == 200

    # now access admin users page
    resp2 = client.get('/admin/users')
    assert resp2.status_code == 200
    # basic content check - page should contain HTML title or users table (rendered template)
    assert b"Users" in resp2.data or b"Manage Users" in resp2.data


def test_admin_dashboard_accessible(client, app):
    make_admin(app, username='admin2', password='pw321')
    resp = client.post('/api/auth/login', json={'username': 'admin2', 'password': 'pw321'})
    assert resp.status_code == 200
    resp2 = client.get('/admin/dashboard')
    assert resp2.status_code == 200
    assert b"dashboard" in resp2.data.lower() or b"metrics" in resp2.data.lower()
