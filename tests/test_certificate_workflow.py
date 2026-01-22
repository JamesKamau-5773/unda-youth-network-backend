from services import registration_service
from models import db, Certificate


def test_certificate_created_on_approve(app):
    from services.registration_service import approve_registration
    from models import MemberRegistration, User

    # Create registration
    from services import registration_service
    from models import db, Certificate


    def test_certificate_created_on_approve(app):
        from services.registration_service import approve_registration
        from models import MemberRegistration, User

        # Create registration
        with app.app_context():
            r = MemberRegistration(full_name='Cert User', username='cert_user', phone_number='+254700000000')
            r.set_password('secret')
            db.session.add(r)
            db.session.commit()
            reg_id = r.registration_id

            # Create reviewer
            reviewer = User(username='rev2', role=User.ROLE_ADMIN)
            reviewer.set_password('revpass')
            db.session.add(reviewer)
            db.session.commit()
            reviewer_id = reviewer.user_id

            # Approve registration (should create user and certificate)
            res = approve_registration(reg_id, reviewer_id)
            user = res.get('user')
            assert user is not None

            # Find certificate for user
            cert = Certificate.query.filter_by(user_id=user.user_id).first()
            assert cert is not None
            assert cert.signature is not None


    def test_certificate_verification_endpoint(client, app):
        # Create a certificate entry directly
        from models import User
        import hmac, hashlib
        secret = 'dev-secret'

        with app.app_context():
            u = User(username='verify_user')
            u.set_password('pw')
            db.session.add(u)
            db.session.commit()
            pdf = b'%PDF-1.4\nDummy cert\n%%EOF'
            sig = hmac.new(secret.encode('utf-8'), pdf, hashlib.sha256).hexdigest()
            cert = Certificate(user_id=u.user_id, pdf_data=pdf, signature=sig)
            db.session.add(cert)
            db.session.commit()
            cid = cert.certificate_id

        # Verify via public endpoint
        resp = client.post('/api/certificates/verify', json={'certificate_id': cid, 'signature': sig})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get('valid') is True