import os

from app import create_app


def test_theme_assets_available():
    cfg = {
        'TESTING': True,
        'ENABLE_NEW_THEME': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SECRET_KEY': 'test-secret'
    }
    app, _ = create_app(test_config=cfg)
    client = app.test_client()

    resp_css = client.get('/static/css/theme.css')
    try:
        assert resp_css.status_code == 200
    finally:
        resp_css.close()

    resp_vars = client.get('/static/css/_variables.css')
    try:
        assert resp_vars.status_code == 200
    finally:
        resp_vars.close()

    resp_js = client.get('/static/js/theme-toggle.js')
    try:
        assert resp_js.status_code == 200
    finally:
        resp_js.close()
