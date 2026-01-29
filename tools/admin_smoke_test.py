#!/usr/bin/env python3
"""Smoke-test admin pages with the Flask test client.

Creates a test admin, logs in, requests a list of admin pages, saves
`/admin/affirmations` HTML to `tools/affirmations_output.html`, and scans
pages for problematic strings like 'Item Details', 'Actions', or empty
icon buttons.

Run: python3 tools/admin_smoke_test.py
"""
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app
from models import db, User


PAGES = [
    '/admin/manage-assignments',
    '/admin/affirmations',
    '/admin/media-galleries',
    '/admin/toolkit',
    '/admin/umv-global',
    '/admin/resources',
    '/admin/dashboard',
    '/admin/users',
]

BAD_PATTERNS = [
    'Item Details',
    'Actions',
    'aria-label=""',
    '>\s*</button>',
]


def get_app():
    result = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:', 'WTF_CSRF_ENABLED': False})
    return result[0] if isinstance(result, tuple) else result


def main():
    app = get_app()

    with app.app_context():
        db.create_all()

        # create admin
        username = 'smoketestadmin'
        password = 'secret'
        u = User(username=username, role='Admin')
        u.set_password(password)
        db.session.add(u)
        db.session.commit()

        client = app.test_client()

        rv = client.post('/auth/login', data={'username': username, 'password': password}, follow_redirects=True)
        if rv.status_code != 200:
            print('Login failed, status:', rv.status_code)
            print(rv.data[:1000])
            return 2

        results = []
        for p in PAGES:
            r = client.get(p)
            html = r.data.decode('utf-8', errors='replace')
            found = []
            for pat in BAD_PATTERNS:
                if pat in html:
                    found.append(pat)

            # Save affirmations HTML for manual inspection
            if p == '/admin/affirmations':
                out_path = os.path.join(PROJECT_ROOT, 'tools', 'affirmations_output.html')
                with open(out_path, 'w', encoding='utf-8') as fh:
                    fh.write(html)

            results.append((p, r.status_code, found))

        # Print summary
        print('Admin pages smoke test results:')
        any_fail = False
        for p, status, found in results:
            line = f"{p}: {status}"
            if found:
                line += ' — found patterns: ' + ', '.join(found)
                any_fail = True
            print(line)

        if any_fail:
            print('\nAffirmations HTML written to tools/affirmations_output.html for inspection.')
            return 1
        return 0


if __name__ == '__main__':
    sys.exit(main())
