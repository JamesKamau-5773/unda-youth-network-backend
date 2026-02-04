import pytest
from models import db, User


def test_registration_profile_fields_persist(client, app):
    # Create a registration with profile fields
    payload = {
        'full_name': 'Fields User',
        'phone_number': '0712223333',
        'username': 'fields_user',
        'password': 'FieldsPass1!',
        'date_of_birth': '1995-06-15',
        'gender': 'Female',
        'county_sub_county': 'Nairobi, Westlands'
    }

    rv = client.post('/api/auth/register', json=payload)
    assert rv.status_code == 201
    data = rv.get_json()
    reg_id = data['data']['registration_id']

    # Create admin and login
    with app.app_context():
        admin = User(username='fields_admin')
        admin.set_password('AdminPass1!')
        admin.set_role(User.ROLE_ADMIN)
        db.session.add(admin)
        db.session.commit()

    login_resp = client.post('/api/auth/login', json={'username': 'fields_admin', 'password': 'AdminPass1!'})
    assert login_resp.status_code == 200

    # Approve registration
    approve = client.post(f'/api/admin/registrations/{reg_id}/approve')
    assert approve.status_code == 200
    body = approve.get_json()
    created_username = body.get('username') or payload['username']

    # Verify persisted user profile fields
    with app.app_context():
        user = User.query.filter_by(username=created_username).first()
        assert user is not None
        assert user.date_of_birth is not None
        assert str(user.date_of_birth) == '1995-06-15'
        assert getattr(user, 'gender', None) == 'Female'
        assert getattr(user, 'county_sub_county', None) == 'Nairobi, Westlands'
