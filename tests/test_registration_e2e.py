import pytest
from models import db, User


def test_public_signup_approve_and_login(client, app):
    # Public registration (JSON API) - omit username to test auto-generation
    payload = {
        'fullName': 'End To End User',
        'phoneNumber': '+254712345679',
        'password': 'StrongPass1!',
        'email': 'e2e@example.com'
    }

    rv = client.post('/api/auth/register', json=payload)
    assert rv.status_code == 201
    data = rv.get_json()
    reg_id = data['data']['registration_id']

    # Create an admin and authenticate via session for admin API
    with app.app_context():
        admin = User(username='e2e_admin')
        admin.set_password('AdminPass1!')
        admin.role = User.ROLE_ADMIN
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.user_id

    # Set flask-login session directly to impersonate admin
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_id)

    # Approve registration via admin API
    rv = client.post(f'/api/admin/registrations/{reg_id}/approve')
    assert rv.status_code == 200
    resp = rv.get_json()
    assert resp.get('message') == 'Registration approved successfully'
    username = resp.get('username')
    assert username

    # Login using API with approved user's credentials
    login_payload = {'username': username, 'password': 'StrongPass1!'}
    rv = client.post('/api/auth/login', json=login_payload)
    assert rv.status_code == 200
    body = rv.get_json()
    assert body.get('user') and body['user']['username'] == username
