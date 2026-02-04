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


# Provide transactional test isolation via nested savepoints. This lets the
# session-scoped schema and any seed data created at session setup remain
# visible to tests while ensuring changes made inside each test are rolled
# back afterwards.
@pytest.fixture(autouse=True)
def db_transaction(app):
    import sqlalchemy as sa
    from sqlalchemy import event

    # Use the application context when creating engine connections and
    # sessions so Flask-SQLAlchemy can resolve the current app config.
    with app.app_context():
        # Create a new connection and begin an outer transaction for the test
        connection = _db.engine.connect()
        outer_transaction = connection.begin()

        # Bind a scoped session to the connection using SQLAlchemy primitives
        from sqlalchemy.orm import sessionmaker, scoped_session

        original_session = _db.session
        # Prevent objects from being expired on commit so tests can safely
        # access attributes off instances after commits without triggering
        # lazy-loads against a now-detached session.
        session_factory = sessionmaker(bind=connection, expire_on_commit=False)
        Session = scoped_session(session_factory)
        _db.session = Session

        # Start a nested transaction (SAVEPOINT) for test-level rollback
        nested = _db.session().begin_nested()

        # Ensure a clean slate for tests: remove any leftover registrations
        # that might have been created outside the proxied session in previous runs.
        try:
            connection.execute(sa.text('DELETE FROM member_registrations'))
        except Exception:
            # If table doesn't exist yet or deletion fails, ignore and continue.
            pass

        # Ensure SAVEPOINT is restarted when the session issues a new transaction
        @event.listens_for(_db.session(), "after_transaction_end")
        def restart_savepoint(sess, trans):
            if trans.nested and not sess.is_active:
                sess.begin_nested()

        try:
            yield _db.session
        finally:
            # Teardown must also occur within app context
            try:
                # Remove the scoped session created for this test
                _db.session.remove()
            except Exception:
                pass
            try:
                # Only rollback if still active to avoid SAWarning about
                # already-dissociated transactions on some DB backends.
                if outer_transaction.is_active:
                    outer_transaction.rollback()
            except Exception:
                pass
            try:
                connection.close()
            except Exception:
                pass
            # Restore the original session factory
            _db.session = original_session


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
    yield app

    # Teardown - drop all tables for the session
    with app.app_context():
        try:
            _db.session.remove()
        except Exception:
            pass
        try:
            _db.engine.dispose()
        except Exception:
            pass
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
