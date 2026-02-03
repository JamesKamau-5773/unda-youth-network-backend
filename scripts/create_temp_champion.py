#!/usr/bin/env python3
"""Create a minimal temporary Champion for a user (local repair script).

Usage:
  REPAIR_ALLOW=true python3 scripts/create_temp_champion.py --username mica

Safety: The script will refuse to run unless the environment variable
`REPAIR_ALLOW` is set to a truthy value. It should be run only by a
developer or operator with DB access.
"""
import os
import sys
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--username', required=True)
    args = parser.parse_args()

    if os.environ.get('REPAIR_ALLOW', '').lower() not in ('1', 'true', 'yes'):
        print('Refusing to run: set REPAIR_ALLOW=true in the environment to allow this script')
        sys.exit(2)

    # Import app factory and models
    # Import factory; `create_app()` may return (app, limiter) so handle both cases
    from app import create_app, flask_app_factory
    from models import db, User, Champion
    from datetime import date
    import secrets

    try:
        # Prefer the flask_app_factory which returns the Flask app instance
        app = flask_app_factory()
    except Exception:
        app_tuple = create_app()
        if isinstance(app_tuple, tuple):
            app = app_tuple[0]
        else:
            app = app_tuple

    with app.app_context():
        username = args.username
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f'User not found: {username}')
            sys.exit(1)

        if getattr(user, 'champion_id', None):
            print(f'User {username} already has champion_id={user.champion_id}')
            sys.exit(0)

        assigned_code = f"TMP{user.user_id}{secrets.token_hex(2)}"
        phone_placeholder = f"+999{100000 + (user.user_id or 0)}"

        champ = Champion(
            user_id=user.user_id,
            full_name=(user.username or f'user{user.user_id}'),
            gender='Other',
            phone_number=phone_placeholder,
            email=user.email,
            assigned_champion_code=assigned_code,
            application_status='Recruited',
            champion_status='Active',
            date_of_application=date.today()
        )
        db.session.add(champ)
        db.session.flush()

        user.champion_id = champ.champion_id
        db.session.add(user)
        db.session.commit()

        print(f'Created champion id={champ.champion_id} assigned_code={assigned_code} for user={username}')
        sys.exit(0)
