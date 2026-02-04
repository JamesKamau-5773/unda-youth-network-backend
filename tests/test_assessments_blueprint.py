from datetime import date


def test_validate_champion_and_submit_with_referral(client, app):
    from models import Champion, User, db

    with app.app_context():
        # Create a champion record
        champ = Champion(full_name='C One', gender='Female', phone_number='+254700000000', assigned_champion_code='TESTCHP', date_of_application=date.today())
        db.session.add(champ)

        # Create a prevention advocate user
        ua = User(username='advocate1')
        ua.set_password('Adv0cate!')
        ua.set_role('Prevention Advocate')
        db.session.add(ua)
        db.session.commit()

    # Login as advocate
    resp = client.post('/api/auth/login', json={'username': 'advocate1', 'password': 'Adv0cate!'})
    assert resp.status_code == 200

    # Validate champion code
    r = client.post('/api/assessments/validate-champion-code', json={'champion_code': 'testchp'})
    assert r.status_code == 200
    jr = r.get_json()
    assert jr.get('valid') is True

    # Submit PHQ-9 assessment with a score that does NOT trigger auto-referral (e.g., 12 -> Purple)
    payload = {
        'champion_code': 'TESTCHP',
        'assessment_type': 'PHQ-9',
        'raw_score': 12,
        'is_baseline': False,
        'notes': 'Screening test'
    }
    r2 = client.post('/api/assessments/submit', json=payload)
    assert r2.status_code == 201
    j2 = r2.get_json()
    assert j2.get('success') is True
    assert j2.get('referral_created') is False
    assert j2.get('referral_id') is None


def test_my_submissions_returns_recent(client, app):
    from models import User

    # Login as previously created advocate
    # Ensure advocate1 exists (some test runs isolate state differently)
    with app.app_context():
        if not User.query.filter_by(username='advocate1').first():
            u = User(username='advocate1')
            u.set_password('Adv0cate!')
            u.set_role('Prevention Advocate')
            from models import db
            db.session.add(u)
            db.session.commit()

    resp = client.post('/api/auth/login', json={'username': 'advocate1', 'password': 'Adv0cate!'})
    assert resp.status_code == 200

    r = client.get('/api/assessments/my-submissions')
    assert r.status_code == 200
    jr = r.get_json()
    assert jr.get('success') is True
    assert 'assessments' in jr
