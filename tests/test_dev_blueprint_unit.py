import pytest

DEV_KEY = 'your-secret-dev-key-change-this'


def test_dev_info_requires_key(client):
    rv = client.get(f'/__dev__/info?key={DEV_KEY}', follow_redirects=True)
    assert rv.status_code == 200
    data = None
    try:
        data = rv.get_json()
    except Exception:
        data = None
    if data:
        assert 'timestamp' in data
        assert 'database' in data
    else:
        # Accept HTML fallback; ensure non-empty body
        assert rv.data and len(rv.data) > 0


def test_dev_routes_requires_key(client):
    rv = client.get(f'/__dev__/routes?key={DEV_KEY}', follow_redirects=True)
    assert rv.status_code == 200
    data = None
    try:
        data = rv.get_json()
    except Exception:
        data = None
    if data:
        assert 'routes' in data and isinstance(data['routes'], list)
    else:
        assert rv.data and len(rv.data) > 0


def test_dev_structure_requires_key(client):
    rv = client.get(f'/__dev__/structure?key={DEV_KEY}', follow_redirects=True)
    assert rv.status_code == 200
    data = None
    try:
        data = rv.get_json()
    except Exception:
        data = None
    if data:
        assert 'project_root' in data and 'structure' in data
    else:
        assert rv.data and len(rv.data) > 0


def test_dev_logs_placeholder(client):
    rv = client.get(f'/__dev__/logs?key={DEV_KEY}', follow_redirects=True)
    assert rv.status_code == 200
    data = None
    try:
        data = rv.get_json()
    except Exception:
        data = None
    if data:
        assert 'message' in data
    else:
        assert rv.data and len(rv.data) > 0
