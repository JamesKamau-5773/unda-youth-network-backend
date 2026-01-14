"""Run Alembic migrations programmatically against a local SQLite dev DB."""
from app import create_app
from flask_migrate import upgrade

if __name__ == '__main__':
    config = {
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///dev.sqlite',
        'TESTING': False,
        'WTF_CSRF_ENABLED': False
    }
    app, _ = create_app(test_config=config)
    with app.app_context():
        upgrade()
        print('Migrations applied')
