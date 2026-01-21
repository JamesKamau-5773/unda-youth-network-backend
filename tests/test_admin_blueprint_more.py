import pytest
from datetime import datetime, timezone

from models import db, MemberRegistration, ChampionApplication, Podcast, User


def login(client, username, password):
    return client.post('/auth/login', data={'username': username, 'password': password}, follow_redirects=True)


def test_approve_and_reject_registration(app, client):
    with app.app_context():
        admin = User(username='reg_admin')
        admin.set_password('RegAdmin1!')
        admin.set_role('Admin')
        db.session.add(admin)

        reg = MemberRegistration(full_name='Test Person', username='newmember', phone_number='0712345678')
        reg.set_password('memberpass1!')
        db.session.add(reg)
        db.session.commit()
        reg_id = reg.registration_id

    rv = login(client, 'reg_admin', 'RegAdmin1!')
    assert rv.status_code == 200

    # Approve registration
    rv = client.post(f'/admin/registrations/{reg_id}/approve', follow_redirects=True)
    assert rv.status_code == 200
    assert b'approved' in rv.data or b'has been approved' in rv.data

    with app.app_context():
        r = db.session.get(MemberRegistration, reg_id)
        assert r.status == 'Approved'

    # Create another registration to reject
    with app.app_context():
        reg2 = MemberRegistration(full_name='Reject Me', username='rejectme', phone_number='0700000000')
        reg2.set_password('passReject1!')
        db.session.add(reg2)
        db.session.commit()
        reg2_id = reg2.registration_id

    rv = client.post(f'/admin/registrations/{reg2_id}/reject', data={'reason': 'Invalid'}, follow_redirects=True)
    assert rv.status_code == 200
    assert b'Registration has been rejected' in rv.data or b'rejected' in rv.data

    with app.app_context():
        r2 = db.session.get(MemberRegistration, reg2_id)
        assert r2.status == 'Rejected'


def test_approve_and_reject_champion_application(app, client):
    with app.app_context():
        admin = User(username='app_admin')
        admin.set_password('AppAdmin1!')
        admin.set_role('Admin')
        db.session.add(admin)

        # Need a user to link application to
        applicant = User(username='applicant_user')
        applicant.set_password('Applicant1!')
        db.session.add(applicant)
        db.session.commit()
        applicant_id = applicant.user_id

        app_record = ChampionApplication(user_id=applicant_id, full_name='Applicant', phone_number='0701112222', gender='Other', date_of_birth=datetime(2000,1,1))
        db.session.add(app_record)
        db.session.commit()
        app_id = app_record.application_id

    rv = login(client, 'app_admin', 'AppAdmin1!')
    assert rv.status_code == 200

    rv = client.post(f'/admin/champion-applications/{app_id}/approve', follow_redirects=True)
    assert rv.status_code == 200
    assert b'approved' in rv.data or b'has been approved' in rv.data

    with app.app_context():
        a = db.session.get(ChampionApplication, app_id)
        assert a.status == 'Approved'

    # Reject flow
    with app.app_context():
        app2 = ChampionApplication(user_id=applicant_id, full_name='Applicant2', phone_number='0703334444', gender='Female', date_of_birth=datetime(2001,1,1))
        db.session.add(app2)
        db.session.commit()
        app2_id = app2.application_id

    rv = client.post(f'/admin/champion-applications/{app2_id}/reject', data={'reason': 'Incomplete'}, follow_redirects=True)
    assert rv.status_code == 200
    assert b'Application has been rejected' in rv.data or b'rejected' in rv.data

    with app.app_context():
        a2 = db.session.get(ChampionApplication, app2_id)
        assert a2.status == 'Rejected'


def test_toggle_publish_podcast(app, client):
    with app.app_context():
        admin = User(username='pod_admin')
        admin.set_password('PodAdmin1!')
        admin.set_role('Admin')
        db.session.add(admin)

        p = Podcast(title='Test Ep', audio_url='http://audio', published=False)
        db.session.add(p)
        db.session.commit()
        pid = p.podcast_id

    rv = login(client, 'pod_admin', 'PodAdmin1!')
    assert rv.status_code == 200

    rv = client.post(f'/admin/podcasts/{pid}/toggle-publish', follow_redirects=True)
    assert rv.status_code == 200
    assert b'published' in rv.data or b'Podcast published' in rv.data or b'Podcast unpublished' in rv.data

    with app.app_context():
        p2 = db.session.get(Podcast, pid)
        assert p2.published is True
