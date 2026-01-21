import json
from models import db, User, MemberRegistration


def test_register_member_success(client):
    payload = {
        'full_name': 'Test User',
        'phone_number': '0712345678',
        'username': 'testuser1',
        'password': 'VeryStrongP@ss1'
    }
    resp = client.post('/api/auth/register', json=payload)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data.get('success') is True
    assert 'registration_id' in data.get('data')

    # Ensure MemberRegistration exists in DB
    reg_id = data['data']['registration_id']
    with client.application.app_context():
        reg = db.session.get(MemberRegistration, reg_id)
        assert reg is not None
        assert reg.username == 'testuser1'


def test_register_missing_field_returns_422(client):
    payload = {
        'full_name': 'No Username',
        'phone_number': '0712345678',
        'password': 'AnotherStrong1'
    }
    resp = client.post('/api/auth/register', json=payload)
    assert resp.status_code == 422
    data = resp.get_json()
    assert data.get('success') is False
    assert 'error' in data


def test_api_login_and_failed_login_tracking(client, app):
    # create a user
    with app.app_context():
        u = User(username='loginuser', email='login@example.com')
        u.set_password('CorrectHorseBattery1!')
        u.set_role(User.ROLE_PREVENTION_ADVOCATE)
        db.session.add(u)
        db.session.commit()

    # attempt wrong password
    r1 = client.post('/api/auth/login', json={'username': 'loginuser', 'password': 'wrongpass'})
    assert r1.status_code == 401

    # now correct password
    r2 = client.post('/api/auth/login', json={'username': 'loginuser', 'password': 'CorrectHorseBattery1!'})
    assert r2.status_code == 200
    body = r2.get_json()
    assert body.get('user')['username'] == 'loginuser'
