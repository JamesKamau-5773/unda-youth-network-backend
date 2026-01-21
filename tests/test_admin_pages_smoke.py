from models import db, User


def create_user(app, username='admin', role='Admin', password='secret'):
    with app.app_context():
        u = User(username=username, role=role)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        return u.user_id


def login(client, username, password='secret'):
    return client.post('/auth/login', data={'username': username, 'password': password}, follow_redirects=True)


def test_admin_pages_smoke(client, app):
    admin_id = create_user(app, username='pageadmin', role='Admin')
    login(client, 'pageadmin')

    paths = [
        '/admin/manage-assignments',
        '/admin/affirmations',
        '/admin/media-galleries',
        '/admin/toolkit',
        '/admin/umv-global',
        '/admin/resources'
    ]

    for p in paths:
        rv = client.get(p)
        assert rv.status_code == 200
