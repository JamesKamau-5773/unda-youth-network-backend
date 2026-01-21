from datetime import date


def test_admin_get_registrations_and_approve(client, app):
    from models import User, MemberRegistration, db

    with app.app_context():
        # Create admin user
        admin = User(username='admin_test')
        admin.set_password('Admin!234')
        admin.set_role('Admin')
        db.session.add(admin)
        db.session.commit()

        # Create a pending registration
        reg = MemberRegistration(
            full_name='Pending One',
            email='p1@example.com',
            phone_number='+254712345678',
            username='pending_user',
            date_of_birth=date(2000,1,1),
            gender='Female',
            county_sub_county='Nairobi'
        )
        reg.set_password('Str0ng!Pass')
        db.session.add(reg)
        db.session.commit()
        rid = reg.registration_id

    # Login as admin
    resp = client.post('/api/auth/login', json={'username': 'admin_test', 'password': 'Admin!234'})
    assert resp.status_code == 200

    # Fetch registrations (should return at least our pending one)
    r = client.get('/api/admin/registrations')
    assert r.status_code == 200
    j = r.get_json()
    assert 'registrations' in j

    # Approve the registration
    r2 = client.post(f'/api/admin/registrations/{rid}/approve')
    assert r2.status_code == 200
    data = r2.get_json()
    assert data.get('message') == 'Registration approved successfully'
