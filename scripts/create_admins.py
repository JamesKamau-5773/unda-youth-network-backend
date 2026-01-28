#!/usr/bin/env python3
"""
List existing admin users and create/reset admin accounts for local development.
Prints generated passwords to stdout. Intended for local dev only.
"""
import secrets
from app import flask_app_factory
from models import db, User

app = flask_app_factory()

with app.app_context():
    admins = User.query.filter(User.role.ilike('%admin%')).all()
    print('Existing admin users:')
    if not admins:
        print('  (none found)')
    for u in admins:
        print(f"  - {u.username} (id={u.user_id}) locked={u.account_locked} failed={u.failed_login_attempts}")

    # Accounts to ensure exist / reset
    targets = [
        ('admin', 'admin@example.com'),
        ('dev_admin', 'dev_admin@example.com'),
    ]

    results = []
    for username, email in targets:
        user = User.query.filter_by(username=username).first()
        pwd = secrets.token_urlsafe(12)
        if user:
            user.set_password(pwd)
            user.account_locked = False
            user.failed_login_attempts = 0
            user.locked_until = None
            user.invite_token = None
            user.invite_token_expires = None
            try:
                user.set_role(User.ROLE_ADMIN)
            except Exception:
                user.role = User.ROLE_ADMIN
            db.session.add(user)
            action = 'reset'
        else:
            user = User(username=username, email=email)
            user.set_password(pwd)
            try:
                user.set_role(User.ROLE_ADMIN)
            except Exception:
                user.role = User.ROLE_ADMIN
            db.session.add(user)
            action = 'created'
        db.session.commit()
        results.append((action, username, user.user_id, pwd))

    print('\nAdmin account changes:')
    for action, username, uid, pwd in results:
        print(f"  - {action} {username} (id={uid}) password={pwd}")

    print('\nDone. Please store these credentials securely and rotate them before use in production.')
