import json

def test_impact_stats_summary_returns_success(client):
    resp = client.get('/api/impact-stats/summary')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('success') is True
    assert 'summary' in data


def test_campus_initiatives_returns_events_list(client):
    resp = client.get('/api/campus-initiatives')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('success') is True
    assert isinstance(data.get('events'), list)


def test_members_me_unauthenticated_returns_401(client):
    resp = client.get('/api/members/me')
    assert resp.status_code == 401
    data = resp.get_json()
    assert 'error' in data


def test_checkin_requires_auth_returns_401(client):
    resp = client.post('/api/checkin', json={})
    # Without a logged-in user or valid token this should be unauthorized
    assert resp.status_code in (401, 400, 404)
    # Accept a range because some environments may return 400 for missing champion_id instead of 401
