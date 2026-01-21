#!/usr/bin/env python3
from app import create_app
from models import db, User
import os

os.environ.setdefault('FALLBACK_TO_SQLITE', 'True')
app, _ = create_app()

with app.app_context():
    u = User.query.filter_by(username='admin').first()
    if u:
        print('admin exists:', u.username, 'email=', u.email)
    else:
        u = User(username='admin', email='admin@example.com')
        u.set_password('adminpw')
        u.set_role(User.ROLE_ADMIN)
        db.session.add(u)
        db.session.commit()
        print('Created admin: admin / adminpw')

    admins = User.query.filter_by(role=User.ROLE_ADMIN).all()
    print('Total admins:', len(admins))
    for a in admins:
        print(' -', a.username, a.email)
