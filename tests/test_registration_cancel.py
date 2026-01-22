def test_cancel_with_token(client):
    payload = {
        'full_name': 'Cancel User',
        'phone_number': '0712345678',
        'username': 'cancel_user',
        'password': 'Cancel$tr0ng',
        'email': 'cancel@example.com'
    }

    resp = client.post('/api/auth/register', json=payload)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data.get('success') is True
    reg = data.get('data')
    reg_id = reg.get('registration_id')
    token = reg.get('cancellation_token')

    # Cancel using header token
    resp2 = client.delete(f'/api/auth/registration/{reg_id}', headers={'X-Registration-Token': token})
    assert resp2.status_code == 200
    resp2_data = resp2.get_json()
    assert resp2_data.get('success') is True


def test_cancel_with_invalid_token_forbidden(client):
    payload = {
        'full_name': 'Cancel User 2',
        'phone_number': '0712345777',
        'username': 'cancel_user2',
        'password': 'Cancel$tr0ng2',
        'email': 'cancel2@example.com'
    }

    resp = client.post('/api/auth/register', json=payload)
    assert resp.status_code == 201
    data = resp.get_json()
    reg = data.get('data')
    reg_id = reg.get('registration_id')

    # Attempt cancel with wrong token
    resp2 = client.delete(f'/api/auth/registration/{reg_id}', headers={'X-Registration-Token': 'badtoken'})
    assert resp2.status_code == 403
    resp2_data = resp2.get_json()
    assert resp2_data.get('success') is False
