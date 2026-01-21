import time


def test_create_user_sends_invite(monkeypatch, app):
    from services.user_service import create_user
    from models import db

    with app.app_context():
        # Ensure send_invite returns True without actually sending
        monkeypatch.setattr('services.user_service.send_invite', lambda *a, **k: True)
        unique = str(int(time.time() * 1000))[-6:]
        username = f"svc_user_{unique}"
        out = create_user(username, 'svc@example.com', 'Admin')
        assert out['invite_sent'] is True
        assert out['user'] is not None


def test_reset_password_generates_invite(app):
    from models import User, db
    from services.user_service import reset_password

    with app.app_context():
        u = User(username='reset_user', password_hash='x')
        db.session.add(u)
        db.session.commit()

        out = reset_password(u.user_id)
        # Reset now returns a temporary password for admins to share
        assert 'temp_password' in out
        assert out.get('user') is not None


def test_unlock_and_change_role(app):
    from models import User, db
    from services.user_service import unlock_user, change_role

    with app.app_context():
        u = User(username='role_user', password_hash='x', failed_login_attempts=3, account_locked=True)
        db.session.add(u)
        db.session.commit()

        unlock_user(u.user_id)
        u2 = db.session.get(User, u.user_id)
        assert u2.failed_login_attempts == 0

        res = change_role(u.user_id, 'Admin')
        assert res['new_role'] in ('Admin', 'admin'.title())


def test_delete_user_removes_user(app):
    from models import User, db
    from services.user_service import delete_user

    with app.app_context():
        a = User(username='victim', password_hash='x')
        b = User(username='executor', password_hash='x')
        db.session.add_all([a, b])
        db.session.commit()

        # executor deletes victim
        delete_user(a.user_id, b.user_id)
        assert db.session.get(User, a.user_id) is None
