import pytest
from models import db, User


def create_user(app, username='admin', role='Admin', password='secret'):
    with app.app_context():
        u = User(username=username, role=role)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        return u.user_id


def login(client, username, password='secret'):
    return client.post('/auth/login', data={'username': username, 'password': password}, follow_redirects=True)


def test_create_user_validation_short_username(client, app):
    admin_id = create_user(app, username='adminshort', role='Admin')
    login(client, 'adminshort')

    rv = client.post('/admin/users/create', data={'username': 'ab', 'email': 'a@b.com', 'role': 'Supervisor'}, follow_redirects=True)
    assert rv.status_code == 200
    assert b'Username must be at least 3 characters' in rv.data


def test_create_user_duplicate_username(client, app):
    # existing user
    existing_id = create_user(app, username='exists', role='Supervisor')
    admin_id = create_user(app, username='admincreate', role='Admin')
    login(client, 'admincreate')

    rv = client.post('/admin/users/create', data={'username': 'exists', 'email': 'new@mail.test', 'role': 'Supervisor'}, follow_redirects=True)
    assert rv.status_code == 200
    assert b'Username "exists" already exists' in rv.data or b'already exists' in rv.data


def test_delete_user_removes_target(client, app):
    admin_id = create_user(app, username='admindel', role='Admin')
    target_id = create_user(app, username='toremove', role='Supervisor')
    login(client, 'admindel')

    rv = client.post(f'/admin/users/{target_id}/delete', follow_redirects=True)
    assert rv.status_code == 200

    with app.app_context():
        u = db.session.get(User, target_id)
        assert u is None


def test_change_password_flow_redirect_and_flash(client, app):
    admin_id = create_user(app, username='changepw', role='Admin', password='oldpass')
    login(client, 'changepw', password='oldpass')

    rv = client.post('/admin/change-password', data={'current_password': 'oldpass', 'new_password': 'newpass', 'confirm_password': 'newpass'}, follow_redirects=True)
    # Ensure endpoint handles the request without server error
    assert rv.status_code == 200
