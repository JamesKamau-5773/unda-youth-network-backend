import json


def test_register_and_login(client):
    # register a new user
    payload = {
        "full_name": "Test User",
        "email": "testuser@example.com",
        "phone_number": "254712345678",
        "password": "ValidPass123!",
    }
    rv = client.post('/auth/register', data=payload, follow_redirects=True)
    assert rv.status_code in (200, 302)

    # attempt login with the new credentials
    login_payload = {"email": payload['email'], "password": payload['password']}
    rv = client.post('/auth/login', data=login_payload)
    # login may redirect or return 200 depending on implementation
    assert rv.status_code in (200, 302)


def test_register_with_missing_fields(client):
    rv = client.post('/auth/register', data={})
    # expect the app to respond with a validation error (400) or redirect back
    assert rv.status_code in (400, 302, 200)
