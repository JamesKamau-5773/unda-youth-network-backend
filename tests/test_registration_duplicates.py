import time


def test_duplicate_registration_blocks_when_pending(client):
    unique = str(int(time.time() * 1000))[-6:]
    username = f"dupuser_{unique}"
    payload = {
        'full_name': 'Duplicate User',
        'phone_number': '0712345678',
        'username': username,
        'password': 'Str0ng!Pass1',
        'email': f'dup{unique}@example.com'
    }

    # First registration should succeed
    resp1 = client.post('/api/auth/register', json=payload)
    assert resp1.status_code == 201

    # Second registration with same username/phone/email should be blocked (409)
    resp2 = client.post('/api/auth/register', json=payload)
    assert resp2.status_code == 409
    data = resp2.get_json()
    assert data.get('success') is False
    assert 'error' in data


def test_registration_allowed_after_rejected(app, client):
    # Create a prior rejected registration (different username but same contact)
    from models import db, MemberRegistration

    with app.app_context():
        # Use a phone number that won't clash with the pending registration
        existing = MemberRegistration(full_name='Old Reg', username='old_reg', phone_number='+254791111111', email='old@example.com')
        existing.set_password('secret')
        existing.status = 'Rejected'
        db.session.add(existing)
        db.session.commit()

    # New registration with same phone/email but a new username should be allowed
    payload = {
        'full_name': 'New Applicant',
        'phone_number': '0791111111',
        'username': 'new_applicant',
        'password': 'Another$tr0ng1',
        'email': 'old@example.com'
    }

    resp = client.post('/api/auth/register', json=payload)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data.get('success') is True
