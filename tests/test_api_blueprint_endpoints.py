import os


def test_impact_stats_endpoint(client):
    resp = client.get('/api/impact-stats')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('success') is True
    assert 'stats' in data
    assert 'overview' in data['stats']


def test_impact_stats_summary_endpoint(client):
    resp = client.get('/api/impact-stats/summary')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('success') is True
    assert 'summary' in data


def test_campus_initiatives_empty(client):
    resp = client.get('/api/campus-initiatives')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('success') is True
    assert isinstance(data.get('events'), list)


def test_members_me_unauthenticated(client):
    resp = client.get('/api/members/me')
    assert resp.status_code == 401


def test_update_current_member_requires_auth_or_token(client):
    resp = client.put('/api/members/me', json={})
    assert resp.status_code == 401


def test_checkin_requires_auth_or_token(client):
    resp = client.post('/api/checkin', json={})
    assert resp.status_code == 401
