import os
import sys
import datetime
import pytest

# Ensure project root is on sys.path for conftest imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services import file_utils
from app import create_app
from models import db as _db
import os as _os


@pytest.fixture(autouse=True)
def mock_save_file(monkeypatch, tmp_path):
    """Replace `save_file` with a lightweight fake that returns a predictable path.

    This prevents tests from writing to disk while preserving the returned
    path value used by services to populate DB records.
    """
    def _fake_save_file(fileobj, subdir='uploads'):
        filename = getattr(fileobj, 'filename', 'file.bin')
        ts = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S%f')
        # Return a relative-ish path consistent with existing code expectations
        return os.path.join(subdir, f"{ts}_{filename}")

    monkeypatch.setattr(file_utils, 'save_file', _fake_save_file)
    yield


# Provide a Flask `app` fixture configured for testing with an in-memory SQLite DB
@pytest.fixture(scope='session')
def app():
    # Do not force-disable email here so development email functionality remains available.
    # Tests that need to avoid sending real emails should mock email sending explicitly.
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,  # Disable CSRF in tests
    }
    app, _ = create_app(test_config)

    # Create DB schema for the test session
    with app.app_context():
        _db.create_all()
        # (connect listener removed) debug instrumentation was temporary
    yield app

    # Teardown - drop all tables
    with app.app_context():
        _db.session.remove()
        try:
            # Close any pooled DB connections to avoid ResourceWarnings
            _db.engine.dispose()
        except Exception:
            pass
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
