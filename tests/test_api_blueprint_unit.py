def test_api_impact_stats_and_campus_initiatives(client):
    # Basic smoke tests for API endpoints
    r = client.get('/api/impact-stats/summary')
    assert r.status_code in (200, 204, 404)

    r2 = client.get('/api/campus-initiatives')
    assert r2.status_code in (200, 204, 404)
