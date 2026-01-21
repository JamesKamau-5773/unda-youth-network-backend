import os
from app import create_app

# Ensure sqlite DB is used when DATABASE_URL env var not provided
os.environ.setdefault('DATABASE_URL', 'sqlite:///dev_smoke.db')
os.environ.setdefault('FLASK_ENV', 'development')
os.environ.setdefault('CLEAN_BREAK_MODE', 'skip_migrations')

_app, _ = create_app()
# Create database tables for smoke tests if they don't exist
try:
    from models import db as _db
    with _app.app_context():
        _db.create_all()
except Exception:
    # If table creation fails, continue and let the app surface errors
    pass

if __name__ == '__main__':
    # Enable debug for local smoke tests to show stack traces in logs
    _app.run(host='127.0.0.1', port=5001, debug=True)
