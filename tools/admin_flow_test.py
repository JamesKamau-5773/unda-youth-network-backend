#!/usr/bin/env python3
"""Boot the Flask app in TESTING mode, create a temporary admin, log in,
and exercise the /admin/affirmations admin flow using the Flask test client.

Run: python3 tools/admin_flow_test.py
"""
import sys
import os
# Ensure project root is on sys.path so imports like `from app import create_app` work
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app
from models import db, User


def main():
    result = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
    })
    app = result[0] if isinstance(result, tuple) else result

    with app.app_context():
        db.create_all()

        # Create admin user
        username = 'testadmin'
        password = 'secret'
        u = User(username=username, role='Admin')
        u.set_password(password)
        db.session.add(u)
        db.session.commit()

        client = app.test_client()

        # Login
        rv = client.post('/auth/login', data={'username': username, 'password': password}, follow_redirects=True)
        print('Login status:', rv.status_code)
        if b'Invalid' in rv.data or rv.status_code != 200:
            print('Login may have failed; response excerpt:')
            print(rv.data[:1000])

        # Access the admin affirmations page
        rv = client.get('/admin/affirmations')
        print('/admin/affirmations status:', rv.status_code)
        print('Response length:', len(rv.data))
        print('Response excerpt:')
        print(rv.data[:1200].decode('utf-8', errors='replace'))

        return 0 if rv.status_code == 200 else 1


if __name__ == '__main__':
    sys.exit(main())
