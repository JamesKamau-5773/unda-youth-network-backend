"""Programmatically reproduce the admin toolkit create flow.

Usage:
  .venv/bin/python scripts/reproduce_toolkit_create.py

This script will:
 - Ensure a `test_admin` account exists (password: TestPass1234)
 - Log in via `/auth/login` (extracting CSRF)
 - GET `/admin/toolkit/create` (extract CSRF)
 - POST a create form and print the response status and body

Useful for debugging 400/500 responses and inspecting response HTML.
"""
import re
import sys
import requests
from app import create_app

def ensure_test_admin():
    app,_ = create_app()
    with app.app_context():
        from models import db, User
        name='test_admin'
        pw='TestPass1234'
        u = User.query.filter_by(username=name).first()
        if not u:
            u = User(username=name, email=f'{name}@example.com')
            u.set_role(User.ROLE_ADMIN)
            u.set_password(pw)
            db.session.add(u)
            db.session.commit()
            print('Created test_admin')
        else:
            u.set_password(pw)
            u.set_role(User.ROLE_ADMIN)
            db.session.add(u)
            db.session.commit()
            print('Reset test_admin password')
    return name, 'TestPass1234'

def extract_csrf(html):
    m = re.search(r'name=["\']csrf_token["\'] value=["\']([^"\']+)["\']', html)
    return m.group(1) if m else None

def main():
    base='http://127.0.0.1:5000'
    name, pw = ensure_test_admin()

    s = requests.Session()
    try:
        r = s.get(base + '/auth/login', timeout=5)
    except Exception as e:
        print('Failed to GET /auth/login:', e); sys.exit(1)
    print('/auth/login', r.status_code)
    token = extract_csrf(r.text)
    if not token:
        print('No csrf found in login page; aborting. Preview:')
        print(r.text[:2000])
        sys.exit(1)

    # Login
    r2 = s.post(base + '/auth/login', data={'username':name,'password':pw,'csrf_token':token}, timeout=5)
    print('/auth/login POST', r2.status_code)

    # GET create form
    r3 = s.get(base + '/admin/toolkit/create', timeout=5)
    print('/admin/toolkit/create GET', r3.status_code)
    token2 = extract_csrf(r3.text)
    if not token2:
        print('No csrf in create form; dumping page for inspection')
        print(r3.text[:4000])
        sys.exit(1)

    # POST create
    data = {'title':'Prog Test Item','content':'Automated test','attachments':'[]','csrf_token':token2}
    r4 = s.post(base + '/admin/toolkit/create', data=data, timeout=10)
    print('/admin/toolkit/create POST ->', r4.status_code)
    print('Headers:', dict(r4.headers))
    print('Body (first 4000 chars):')
    print(r4.text[:4000])

if __name__ == '__main__':
    main()
