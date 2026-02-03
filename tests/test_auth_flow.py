import pytest
from app import create_app
from models import db, User


def setup_test_app():
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key'
    }
    app, _ = create_app(test_config=test_config)
    return app


def test_login_refresh_logout_flow():
    app = setup_test_app()
    with app.app_context():
        db.create_all()
        # create user
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        user.set_role(User.ROLE_PREVENTION_ADVOCATE)
        db.session.add(user)
        db.session.commit()

    client = app.test_client()

    # Login via API JSON
    resp = client.post('/api/auth/login', json={'username': 'testuser', 'password': 'password123'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'access_token' in data
    # Refresh token cookie should be set in response headers
    set_cookie_1 = resp.headers.get('Set-Cookie') or ''
    assert 'refresh_token=' in set_cookie_1

    access_token = data['access_token']

    # Call refresh - should return new access_token and rotate cookie
    resp2 = client.post('/api/auth/refresh')
    assert resp2.status_code == 200
    data2 = resp2.get_json()
    assert 'access_token' in data2
    # After refresh, refresh_token cookie should still exist and differ from previous
    set_cookie_2 = resp2.headers.get('Set-Cookie') or ''
    assert 'refresh_token=' in set_cookie_2
    assert set_cookie_2 != set_cookie_1

    # Logout - should clear cookie
    resp3 = client.post('/api/auth/logout')
    assert resp3.status_code == 200
    # After logout cookie header should clear the cookie (empty value)
    set_cookie_3 = resp3.headers.get('Set-Cookie') or ''
    assert 'refresh_token=' in set_cookie_3
    assert ('refresh_token=;' in set_cookie_3) or ('refresh_token=""' in set_cookie_3)
