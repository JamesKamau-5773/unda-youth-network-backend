#!/usr/bin/env python3
from app import app
from models import Champion, User, db

emails = ['jamesnk5773@gmail.com', 'gpjohhnny@gmail.com']

with app.app_context():
    for email in emails:
        users = User.query.filter_by(email=email).all()
        champs = Champion.query.filter_by(email=email).all()
        
        print(f'\n{email}:')
        print(f'  Users: {len(users)}')
        print(f'  Champions: {len(champs)}')
        
        for u in users:
            print(f'    Deleting user: {u.username} (ID: {u.user_id})')
            db.session.delete(u)
        
        for c in champs:
            print(f'    Deleting champion: {c.full_name} (ID: {c.champion_id}, Code: {c.assigned_champion_code})')
            db.session.delete(c)
    
    db.session.commit()
    print('\nDone - All records removed')
