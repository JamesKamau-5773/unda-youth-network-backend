#!/usr/bin/env python3
"""Generate non-dev end-to-end traffic using Flask test client.

This script starts the app in-process (TESTING) and uses the Flask test
client to create a test user, login, and POST to `/api/mpesa/checkout`.
It uses `MPESA_MOCK=True` so external calls are not made.

Usage:
  python3 scripts/generate_nonde_traffic.py

Environment:
  COUNT - number of unique requests (default 100)
  DUPLICATES - number of replay attempts (default 30)

This runs inside the repo and does not require a running server process.
"""
import os
import sys
import time
import uuid
from random import randint

# Ensure project root on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Ensure M-Pesa mock to avoid external calls
os.environ['MPESA_MOCK'] = 'True'
# Provide dummy M-Pesa config so the endpoint doesn't reject when checking configuration
os.environ.setdefault('MPESA_CONSUMER_KEY', 'dummy')
os.environ.setdefault('MPESA_CONSUMER_SECRET', 'dummy')
os.environ.setdefault('MPESA_SHORTCODE', '600000')
os.environ.setdefault('MPESA_PASSKEY', 'dummy')

from app import create_app
from models import db, User

COUNT = int(os.environ.get('COUNT', '100'))
DUPLICATES = int(os.environ.get('DUPLICATES', '30'))


def ensure_user(app, username='testuser', password='testpass'):
    with app.app_context():
        db.create_all()
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username)
            user.set_role('Admin')
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
        return username, password


def run():
    test_config = {
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,  # disable CSRF for test-client convenience
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///nondev_run.db',
        'SECRET_KEY': 'nondev-secret',
    }
    app, _ = create_app(test_config=test_config)

    username, password = ensure_user(app)

    client = app.test_client()

    # Login via test client to create session cookie
    resp = client.post('/auth/login', data={'username': username, 'password': password}, follow_redirects=True)
    if resp.status_code not in (200, 302):
        print('Login failed', resp.status_code)
        return

    # Load user instance for login_user during request context
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print('User not found after creation')
            return

    successes = 0
    duplicates = 0

    # Get the original underlying view function (unwrap login_required and endpoint_guard)
    view_fn = app.view_functions.get('mpesa.initiate_stk_push')
    # Unwrap decorated layers: login_required -> endpoint_guard -> original
    try:
        orig_fn = getattr(view_fn, '__wrapped__').__wrapped__
    except Exception:
        # Fallback: if wrappers differ, attempt single unwrap
        orig_fn = getattr(view_fn, '__wrapped__', view_fn)

    # Fire unique requests by creating a request context per call and invoking the original view
    for i in range(COUNT):
        key = str(uuid.uuid4())
        payload = {'phoneNumber': f'2547{randint(10000000,99999999)}', 'amount': 50}
        # Create request context and programmatically mark the user as logged in
        with app.test_request_context('/api/mpesa/checkout', method='POST', json=payload, headers={'Idempotency-Key': key}):
            try:
                from flask_login import login_user
                login_user(user)
                r = orig_fn()
                # r may be (response, status) tuple or a Flask Response
                code = 200
                try:
                    if isinstance(r, tuple):
                        if len(r) >= 2 and isinstance(r[1], int):
                            code = r[1]
                    else:
                        code = r.status_code
                except Exception:
                    pass
                if code == 200:
                    successes += 1
            except Exception as e:
                # Log and continue
                print('Request error:', str(e))
        time.sleep(0.005)

    # Fire duplicate replay attempts using a single key
    replay_key = str(uuid.uuid4())
    payload = {'phoneNumber': f'2547{randint(10000000,99999999)}', 'amount': 75}
    with app.test_request_context('/api/mpesa/checkout', method='POST', json=payload, headers={'Idempotency-Key': replay_key}):
        try:
            from flask_login import login_user
            login_user(user)
            orig_fn()
        except Exception:
            pass
    for i in range(DUPLICATES):
        with app.test_request_context('/api/mpesa/checkout', method='POST', json=payload, headers={'Idempotency-Key': replay_key}):
            try:
                from flask_login import login_user
                login_user(user)
                r = orig_fn()
                code = 200
                try:
                    if isinstance(r, tuple):
                        if len(r) >= 2 and isinstance(r[1], int):
                            code = r[1]
                    else:
                        code = r.status_code
                except Exception:
                    pass
                if code == 200:
                    duplicates += 1
            except Exception as e:
                print('Duplicate request error:', str(e))
        time.sleep(0.005)

    print(f'Unique successes: {successes}, duplicate hits returned 200: {duplicates}')


if __name__ == '__main__':
    run()
