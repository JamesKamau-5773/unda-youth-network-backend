import pytest
from datetime import datetime, timezone
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


def test_admin_manage_users_accessible(client, app):
    admin_id = create_user(app, username='admintest', role='Admin')

    # login and access manage users page
    rv = login(client, 'admintest')
    assert rv.status_code == 200

    rv = client.get('/admin/users')
    assert rv.status_code == 200


def test_change_user_role_updates_and_flashes(client, app):
    admin_id = create_user(app, username='admintwo', role='Admin')
    user_id = create_user(app, username='targetuser', role='Prevention Advocate')

    login(client, 'admintwo')

    rv = client.post(f'/admin/users/{user_id}/change-role', data={'role': 'Supervisor'}, follow_redirects=True)
    assert rv.status_code == 200
    assert b'Role changed for' in rv.data or b'Role changed' in rv.data


def test_delete_user_cannot_delete_self(client, app):
    admin_id = create_user(app, username='selfdel', role='Admin')
    login(client, 'selfdel')

    rv = client.post(f'/admin/users/{admin_id}/delete', follow_redirects=True)
    assert rv.status_code == 200
    assert b'You cannot delete your own account' in rv.data


def test_admin_create_user_and_reset_unlock(client, app):
    admin_id = create_user(app, username='creator2', role='Admin')
    login(client, 'creator2')

    # Create a new user via admin create form
    rv = client.post('/admin/users/create', data={'username': 'newby', 'email': 'newby@test.com', 'role': 'Supervisor'}, follow_redirects=True)
    assert rv.status_code == 200
    assert b'newby' in rv.data

    # find created user id
    from models import db, User
    with app.app_context():
        u = User.query.filter_by(username='newby').first()
        assert u is not None
        uid = u.user_id

    # Reset password for created user
    rv = client.post(f'/admin/users/{uid}/reset-password', follow_redirects=True)
    assert rv.status_code == 200

    with app.app_context():
        u = db.session.get(User, uid)
        # Reset now sets a temporary password rather than an invite token
        assert u.password_hash is not None
        assert u.invite_token is None

    # Lock the account artificially then unlock via admin endpoint
    with app.app_context():
        u.account_locked = True
        from datetime import datetime, timedelta, timezone
        u.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
        db.session.add(u)
        db.session.commit()

    rv = client.post(f'/admin/users/{uid}/unlock', follow_redirects=True)
    assert rv.status_code == 200

    with app.app_context():
        u = db.session.get(User, uid)
        assert u.failed_login_attempts == 0
        assert u.locked_until is None


def test_create_champion_and_assign_unassign(client, app):
    admin_id = create_user(app, username='createchamp', role='Admin')
    supervisor_id = create_user(app, username='sup1', role='Supervisor')
    # Authenticate by setting the flask-login session directly to avoid rate-limiting
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_id)

    # Create champion via admin form
    now_ts = int(datetime.now(timezone.utc).timestamp())
    uname = f'champ1_{now_ts}'
    email = f'{uname}@test.com'
    phone = f'+2547000{now_ts % 1000000:06d}'

    data = {
        'username': uname,
        'full_name': 'Champion One',
        'email': email,
        'phone_number': phone,
        'gender': 'Female'
    }
    rv = client.post('/admin/champions/create', data=data, follow_redirects=True)
    assert rv.status_code == 200

    from models import Champion, db
    with app.app_context():
        champ = Champion.query.filter_by(email=email).first()
        if champ is None:
            # Provide response body to help diagnose failures when running full suite
            raise AssertionError(f"Champion not created; response body: {rv.data.decode(errors='replace')}")
        champ_id = champ.champion_id

    # Assign champion to supervisor
    rv = client.post(f'/admin/assign-champion/{champ_id}', data={'supervisor_id': supervisor_id}, follow_redirects=True)
    assert rv.status_code == 200

    with app.app_context():
        champ = db.session.get(Champion, champ_id)
        assert champ.supervisor_id == supervisor_id

    # Unassign champion
    rv = client.post(f'/admin/assign-champion/{champ_id}', data={'supervisor_id': ''}, follow_redirects=True)
    assert rv.status_code == 200

    with app.app_context():
        champ = db.session.get(Champion, champ_id)
        assert champ.supervisor_id is None
