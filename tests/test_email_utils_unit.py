import pytest


def test_send_password_email_disabled(app):
    from email_utils import send_password_email
    with app.app_context():
        app.config['DISABLE_EMAILS'] = True
        assert send_password_email('disabled@example.com', 'user', 'temp123') is False


def test_send_email_fallback_on_send_error(app, monkeypatch):
    from email_utils import send_email, mail
    with app.app_context():
        app.config['DISABLE_EMAILS'] = False

        # Force mail.send to raise to exercise the error path
        def _raise(msg):
            raise Exception('SMTP failure')

        monkeypatch.setattr(mail, 'send', _raise)
        assert send_email('x@example.com', 'subj', 'body') is False


def test_send_invite_respects_disable(app):
    from email_utils import send_invite_email
    with app.app_context():
        app.config['DISABLE_EMAIL_IN_BUILD'] = True
        assert send_invite_email('i@example.com', 'invitee', 'tok123') is False
