import pytest
from services import user_service
from models import db, User, Champion


def test_create_user_without_email(app):
    # create user without email
    with app.app_context():
        result = user_service.create_user('u_no_email', None, 'Supervisor')
        user = result['user']
        assert user.username == 'u_no_email'
        assert result['invite_sent'] is False
        assert result['invite_token'] is not None
        assert result['expires_at'] is not None


def test_create_user_with_email_sends(monkeypatch, app):
    sent = {}
    def fake_send_invite(email, username, token, expires_at):
        sent['called'] = True
        return True
    monkeypatch.setattr(user_service, 'send_invite', fake_send_invite)

    with app.app_context():
        res = user_service.create_user('u_with_email', 'test@example.com', 'Admin')
        assert res['invite_sent'] is True
        assert res['user'].email == 'test@example.com'


def test_reset_password_and_invite_url(app):
    with app.app_context():
        u = User(username='pwreset')
        u.set_password('OldPass1!')
        db.session.add(u)
        db.session.commit()
        uid = u.user_id

        res = user_service.reset_password(uid)
        # reset_password now returns a temporary password for admin to share
        assert 'temp_password' in res
        assert res.get('user') is not None


def test_unlock_change_role_delete_and_prevent_self_delete(app):
    with app.app_context():
        a = User(username='adminx')
        a.set_password('Xpass1!')
        db.session.add(a)
        b = User(username='tobedeleted')
        b.set_password('Bpass1!')
        db.session.add(b)
        db.session.commit()
        admin_id = a.user_id
        target_id = b.user_id

        # unlock_user should not raise for existing
        user_service.unlock_user(target_id)

        # change_role works
        out = user_service.change_role(target_id, 'Supervisor')
        assert out['new_role'] == 'Supervisor'

        # cannot delete own account
        with pytest.raises(ValueError):
            user_service.delete_user(admin_id, admin_id)

        # delete other user
        user_service.delete_user(target_id, admin_id)
        assert db.session.get(User, target_id) is None


def test_change_password_validations(app):
    with app.app_context():
        u = User(username='chgpass')
        u.set_password('Start1!Ab')
        db.session.add(u)
        db.session.commit()
        uid = u.user_id

        # wrong current
        with pytest.raises(ValueError):
            user_service.change_password(uid, 'wrong', 'NewPass1!')

        # weak new password
        with pytest.raises(ValueError):
            user_service.change_password(uid, 'Start1!Ab', 'short')

        # similar to current (attempt with same password)
        with pytest.raises(ValueError):
            user_service.change_password(uid, 'Start1!Ab', 'Start1!Ab')

        # successful change
        out = user_service.change_password(uid, 'Start1!Ab', 'NewStrong1!')
        assert out['user'].user_id == uid
