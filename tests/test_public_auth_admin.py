from datetime import date
from models import db, User, MemberRegistration, ChampionApplication, Champion


def make_admin(app, username='admin', password='adminpw'):
    with app.app_context():
        u = User(username=username, email=f"{username}@example.com")
        u.set_password(password)
        u.set_role(User.ROLE_ADMIN)
        db.session.add(u)
        db.session.commit()
        return u


def test_approve_registration_creates_user(client, app):
    # create a pending registration
    with app.app_context():
        reg = MemberRegistration(full_name='Reg User', username='reguser', phone_number='+254712345678')
        reg.set_password('RegPass123!')
        db.session.add(reg)
        db.session.commit()
        reg_id = reg.registration_id

    # make and login as admin
    make_admin(app, 'admin_approve', 'pw1')
    r = client.post('/api/auth/login', json={'username': 'admin_approve', 'password': 'pw1'})
    assert r.status_code == 200

    resp = client.post(f'/api/admin/registrations/{reg_id}/approve')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'user_id' in data

    with app.app_context():
        reg = db.session.get(MemberRegistration, reg_id)
        assert reg.status == 'Approved'
        user = db.session.get(User, data['user_id'])
        assert user is not None
        assert user.username == 'reguser'


def test_reject_registration_sets_reason(client, app):
    with app.app_context():
        reg = MemberRegistration(full_name='Reg2', username='reg2', phone_number='+254712345679')
        reg.set_password('RegPass123!')
        db.session.add(reg)
        db.session.commit()
        reg_id = reg.registration_id

    make_admin(app, 'admin_reject', 'pw2')
    client.post('/api/auth/login', json={'username': 'admin_reject', 'password': 'pw2'})

    resp = client.post(f'/api/admin/registrations/{reg_id}/reject', json={'reason': 'Invalid data'})
    assert resp.status_code == 200
    j = resp.get_json()
    assert j.get('reason') == 'Invalid data'

    with app.app_context():
        reg = db.session.get(MemberRegistration, reg_id)
        assert reg.status == 'Rejected'
        assert reg.rejection_reason == 'Invalid data'


def test_approve_champion_application_creates_champion(client, app):
    with app.app_context():
        u = User(username='appuser')
        u.set_password('pwapp')
        u.set_role(User.ROLE_PREVENTION_ADVOCATE)
        db.session.add(u)
        db.session.commit()

        app_obj = ChampionApplication(
            user_id=u.user_id,
            full_name='App User',
            phone_number='+254700000001',
            gender='M',
            date_of_birth=date(2000, 1, 1)
        )
        db.session.add(app_obj)
        db.session.commit()
        aid = app_obj.application_id

    make_admin(app, 'admin_champ', 'pw3')
    client.post('/api/auth/login', json={'username': 'admin_champ', 'password': 'pw3'})

    resp = client.post(f'/api/admin/champion-applications/{aid}/approve', json={'assigned_champion_code': 'UMV-2026-000001'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'champion_id' in data

    with app.app_context():
        app_obj = db.session.get(ChampionApplication, aid)
        assert app_obj.status == 'Approved'
        champ = db.session.get(Champion, data['champion_id'])
        assert champ is not None
        assert champ.assigned_champion_code == 'UMV-2026-000001'


def test_reject_champion_application_sets_reason(client, app):
    with app.app_context():
        u = User(username='appuser2')
        u.set_password('pwapp2')
        u.set_role(User.ROLE_PREVENTION_ADVOCATE)
        db.session.add(u)
        db.session.commit()

        app_obj = ChampionApplication(
            user_id=u.user_id,
            full_name='App User2',
            phone_number='+254700000002',
            gender='F',
            date_of_birth=date(1998, 5, 5)
        )
        db.session.add(app_obj)
        db.session.commit()
        aid = app_obj.application_id

    make_admin(app, 'admin_rej_champ', 'pw4')
    client.post('/api/auth/login', json={'username': 'admin_rej_champ', 'password': 'pw4'})

    resp = client.post(f'/api/admin/champion-applications/{aid}/reject', json={'reason': 'Not eligible'})
    assert resp.status_code == 200
    j = resp.get_json()
    assert j.get('reason') == 'Not eligible'

    with app.app_context():
        app_obj = db.session.get(ChampionApplication, aid)
        assert app_obj.status == 'Rejected'
        assert app_obj.rejection_reason == 'Not eligible'
