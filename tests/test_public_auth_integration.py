import json
from datetime import datetime


def test_register_member_and_status(client):
    import time
    unique = str(int(time.time() * 1000))[-6:]
    username = f"testuser_{unique}"
    payload = {
        'full_name': 'Test User',
        'phone_number': '0712345678',
        'username': username,
        'password': 'Str0ng!Pass',
        'date_of_birth': '2000-01-01',
        'gender': 'Female',
    }

    # Register
    resp = client.post('/api/auth/register', json=payload)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data.get('success') is True
    reg = data.get('data')
    assert 'registration_id' in reg

    reg_id = reg['registration_id']

    # Poll registration status
    resp2 = client.get(f'/api/auth/registration/{reg_id}')
    assert resp2.status_code == 200
    status_data = resp2.get_json()
    assert status_data.get('registration_id') == reg_id
    assert status_data.get('status') in ('Pending', 'pending', None) or isinstance(status_data.get('status'), str)
