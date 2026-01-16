"""Creates a test user and champion for smoke tests.

This script is runnable from the `scripts/` folder or the repository root.
It ensures the project root is on `sys.path`, imports the app factory,
and tolerates `create_app` returning either `app` or `(app, something)`.
"""
import sys
import os
from pathlib import Path

# Ensure repository root is on sys.path so imports like `from app import create_app` work
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from models import db, User, Champion
from flask_bcrypt import Bcrypt

# Some versions of create_app returned (app, limiter). Handle both shapes.
created = create_app()
if isinstance(created, tuple) or isinstance(created, list):
    app = created[0]
else:
    app = created

with app.app_context():
    bcrypt = Bcrypt()
    username = 'smoketest'
    password = 'Password123!'
    email = 'smoketest@example.com'

    existing = User.query.filter_by(username=username).first()
    if existing:
        print('Test user already exists:', existing.username)
        # Ensure champion exists
        if existing.champion_id:
            c = Champion.query.get(existing.champion_id)
            print('Champion exists:', c and c.full_name)
        else:
            print('No champion linked to existing user')
        print('Exiting.')
        exit(0)

    # Create user
    user = User(username=username, email=email)
    try:
        user.set_role(User.ROLE_PREVENTION_ADVOCATE)
    except Exception:
        # fallback
        user.role = 'Prevention Advocate'

    user.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    db.session.add(user)
    db.session.flush()

    # Create champion profile
    champ_code = f"SM-{str(Champion.query.count()+1).zfill(6)}"
    champion = Champion(
        user_id=user.user_id,
        full_name='Smoke Test Champion',
        gender='F',
        email=email,
        phone_number='+254700000000',
        assigned_champion_code=champ_code,
        application_status='Approved',
        champion_status='Active',
        risk_level='Low'
    )
    db.session.add(champion)
    db.session.flush()

    # Link
    user.champion_id = champion.champion_id
    db.session.add(user)
    db.session.commit()

    print('Created test user:', username)
    print('Password:', password)
    print('Champion code:', champ_code)
