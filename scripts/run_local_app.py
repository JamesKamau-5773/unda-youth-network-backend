#!/usr/bin/env python3
import os
import sys
from multiprocessing import Process

# Ensure project root is on sys.path when run from the scripts/ directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Run the Flask app with a simple SQLite DB and TESTING mode so it starts without external DB
if __name__ == '__main__':
    os.environ.pop('DATABASE_URL', None)
    from app import create_app
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///dev_run.db',
        'SECRET_KEY': 'dev-run-secret',
    }
    app, _ = create_app(test_config=test_config)
    # Ensure the DB file and tables are created
    with app.app_context():
        from models import db
        db.create_all()
    port = int(os.environ.get('PORT', '5000'))
    print(f'Starting local Flask app on 0.0.0.0:{port}')
    app.run(host='0.0.0.0', port=port, debug=False)
