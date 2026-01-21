from email_utils import send_password_email, send_invite_email


def test_send_password_email_disabled(client, app):
    # Ensure config disables emails
    client.application.config['DISABLE_EMAILS'] = True
    with client.application.app_context():
        ok = send_password_email('noone@example.com', 'userx', 'tempPW')
        assert ok is False


def test_send_invite_email_disabled(client, app):
    client.application.config['DISABLE_EMAILS'] = True
    with client.application.app_context():
        ok = send_invite_email('noone@example.com', 'userx', 'token123')
        assert ok is False
