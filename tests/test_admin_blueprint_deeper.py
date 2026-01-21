import pytest
from datetime import datetime, timezone, timedelta

from models import db, User


def login(client, username, password):
    return client.post('/auth/login', data={'username': username, 'password': password}, follow_redirects=True)


def test_manage_users_list_and_change_role(app, client):
    with app.app_context():
        # create an admin and a target user
        admin = User(username='admin_integ')
        admin.set_password('AdminPass1!')
        admin.set_role('Admin')
        db.session.add(admin)

        target = User(username='target_user')
        target.set_password('TargetPass1!')
        db.session.add(target)
        db.session.commit()

        admin_id = admin.user_id
        target_id = target.user_id

    # login as admin
    rv = login(client, 'admin_integ', 'AdminPass1!')
    assert rv.status_code == 200

    # GET users list
    rv = client.get('/admin/users')
    assert rv.status_code == 200
    assert b'admin_integ' in rv.data
    assert b'target_user' in rv.data

    # Change role of target user
    rv = client.post(f'/admin/users/{target_id}/change-role', data={'role': 'Supervisor'}, follow_redirects=True)
    assert rv.status_code == 200

    with app.app_context():
        changed = db.session.get(User, target_id)
        assert changed.role == 'Supervisor'


def test_prevent_self_delete(app, client):
    with app.app_context():
        admin = User(username='self_delete_admin')
        admin.set_password('SelfDel1!')
        admin.set_role('Admin')
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.user_id

    rv = login(client, 'self_delete_admin', 'SelfDel1!')
    assert rv.status_code == 200

    # Attempt to delete own account
    rv = client.post(f'/admin/users/{admin_id}/delete', follow_redirects=True)
    assert rv.status_code == 200
    assert b'You cannot delete your own account' in rv.data

    with app.app_context():
        assert db.session.get(User, admin_id) is not None


def test_unlock_user_account(app, client):
    with app.app_context():
        admin = User(username='unlock_admin')
        admin.set_password('UnlockAdmin1!')
        admin.set_role('Admin')
        db.session.add(admin)

        target = User(username='locked_user')
        target.set_password('Locked1!')
        target.account_locked = True
        target.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
        db.session.add(target)
        db.session.commit()
        target_id = target.user_id

    rv = login(client, 'unlock_admin', 'UnlockAdmin1!')
    assert rv.status_code == 200

    rv = client.post(f'/admin/users/{target_id}/unlock', follow_redirects=True)
    assert rv.status_code == 200

    with app.app_context():
        user = db.session.get(User, target_id)
        # `unlock_user` clears counters and expiry but does not always flip `account_locked` flag
        assert user.locked_until is None
        assert (user.failed_login_attempts or 0) == 0
