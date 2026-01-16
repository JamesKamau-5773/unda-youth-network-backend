from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, User, Champion, MemberRegistration, ChampionApplication, MediaGallery, InstitutionalToolkitItem, UMVGlobalEntry, ResourceItem, BlogPost
from decorators import admin_required
from password_validator import validate_password_strength
from datetime import datetime, date
import re
import sqlalchemy as sa
try:
    import phonenumbers
except Exception:
    phonenumbers = None

public_auth_bp = Blueprint('public_auth', __name__)


def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def normalize_phone(phone, default_region='KE'):
    """Normalize and validate an international phone number.

    Returns the E.164 formatted phone string on success, or `None` on failure.
    If `phonenumbers` is unavailable, falls back to a permissive regex that
    accepts digits and common separators and returns the digits-only string.
    """
    if not phone:
        return None

    # Remove surrounding whitespace
    raw = phone.strip()

    if phonenumbers:
        try:
            # Parse with a sensible default region (Kenya) so local numbers work
            parsed = phonenumbers.parse(raw, default_region)
            if not phonenumbers.is_possible_number(parsed):
                return None
            if not phonenumbers.is_valid_number(parsed):
                return None
            # Return E.164 formatted string (e.g. +254712345678)
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            return None

    # Fallback: accept a sequence of 7-15 digits after removing separators
    digits = re.sub(r"[\s\-\(\)\+]+", "", raw)
    if re.match(r'^\d{7,15}$', digits):
        # Prefer returning digits prefixed with + if original had +, else digits
        return ('+' + digits) if raw.strip().startswith('+') else digits
    return None


@public_auth_bp.route('/api/auth/complete-invite', methods=['POST'])
def complete_invite():
    """Complete an invite/set-password flow using a token sent to the user's email.

    Expects JSON: {"token": "...", "password": "..."}
    """
    try:
        data = request.get_json() or {}
        token = data.get('token')
        password = data.get('password')

        if not token or not password:
            return jsonify({'error': 'Missing token or password'}), 400

        # Find user by invite token
        user = User.query.filter_by(invite_token=token).first()
        if not user:
            return jsonify({'error': 'Invalid or expired invite token'}), 400

        # Check expiry if set
        from datetime import datetime
        if user.invite_token_expires and datetime.utcnow() > user.invite_token_expires:
            return jsonify({'error': 'Invite token has expired'}), 400

        # Validate password strength
        is_valid, error_message = validate_password_strength(password)
        if not is_valid:
            return jsonify({'error': error_message}), 400

        # Set new password and clear invite
        user.set_password(password)
        user.clear_invite()
        db.session.commit()

        return jsonify({'message': 'Password set successfully. You can now log in.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/auth/register', methods=['POST'])
def register_member():
    """Public endpoint for member registration"""
    try:
        data = request.get_json()
        
        # Validate required fields (email is optional)
        required_fields = ['full_name', 'phone_number', 'username', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        # Validate email format if provided
        if data.get('email') and not validate_email(data['email']):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate and normalize phone number (store E.164 when possible)
        normalized_phone = normalize_phone(data['phone_number'], default_region='KE')
        if not normalized_phone:
            return jsonify({'error': 'Invalid phone number format. Provide an international phone (e.g. +254712345678).'}), 400
        
        # Validate password strength
        is_valid, error_message = validate_password_strength(data['password'])
        if not is_valid:
            return jsonify({'error': error_message}), 400
        
        # Check for existing username
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already exists'}), 400
        
        # Check for existing registration with same username
        if MemberRegistration.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Registration with this username already pending'}), 400
        
        # Check for existing email only if provided
        if data.get('email'):
            if Champion.query.filter_by(email=data['email']).first():
                return jsonify({'error': 'Email already registered'}), 400
        
        # Parse date of birth if provided
        date_of_birth = None
        if data.get('date_of_birth'):
            try:
                date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Create registration record
        registration = MemberRegistration(
            full_name=data['full_name'],
            email=data.get('email'),
            phone_number=normalized_phone,
            username=data['username'],
            date_of_birth=date_of_birth,
            gender=data.get('gender'),
            county_sub_county=data.get('county_sub_county')
        )
        registration.set_password(data['password'])
        
        db.session.add(registration)
        db.session.commit()
        
        return jsonify({
            'message': 'Registration submitted successfully. Your account will be reviewed by an administrator.',
            'registration_id': registration.registration_id,
            'status': 'Pending'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/auth/login', methods=['POST'])
def api_login():
    """API endpoint for member/admin login using JSON. Returns JSON and sets session cookie."""
    try:
        data = request.get_json() or {}
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'error': 'Missing username or password'}), 400

        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401

        # Account lockout handling
        if user.is_locked():
            return jsonify({'error': 'Account locked. Try again later.'}), 403

        if not user.check_password(password):
            user.record_failed_login()
            return jsonify({'error': 'Invalid credentials'}), 401

        # Successful login
        from flask_login import login_user
        user.reset_failed_logins()
        login_user(user, remember=True)

        return jsonify({
            'message': 'Logged in successfully',
            'user': {
                'user_id': user.user_id,
                'username': user.username,
                'role': user.role
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/champion/apply', methods=['POST'])
@login_required
def apply_champion():
    """Endpoint for members to apply to become champions"""
    try:
        # Check if user already has a champion profile
        if current_user.champion_id:
            return jsonify({'error': 'You already have a champion profile'}), 400
        
        # Check if user already has a pending application
        existing_app = ChampionApplication.query.filter_by(
            user_id=current_user.user_id,
            status='Pending'
        ).first()
        if existing_app:
            return jsonify({'error': 'You already have a pending champion application'}), 400
        
        data = request.get_json()
        
        # Validate required fields (email is optional)
        required_fields = ['full_name', 'phone_number', 'gender', 'date_of_birth']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        # Validate email if provided
        if data.get('email') and not validate_email(data['email']):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate and normalize phone number
        normalized_phone = normalize_phone(data['phone_number'], default_region='KE')
        if not normalized_phone:
            return jsonify({'error': 'Invalid phone number format. Provide an international phone (e.g. +254712345678).'}), 400
        
        # Parse date of birth
        try:
            date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Calculate age
        today = date.today()
        age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
        if age < 15 or age > 35:
            return jsonify({'error': 'Champions must be between 15 and 35 years old'}), 400
        
        # Create champion application
        application = ChampionApplication(
            user_id=current_user.user_id,
            full_name=data['full_name'],
            email=data.get('email'),
            phone_number=data['phone_number'],
            alternative_phone_number=data.get('alternative_phone_number'),
            gender=data['gender'],
            date_of_birth=date_of_birth,
            county_sub_county=data.get('county_sub_county'),
            emergency_contact_name=data.get('emergency_contact_name'),
            emergency_contact_relationship=data.get('emergency_contact_relationship'),
            emergency_contact_phone=data.get('emergency_contact_phone'),
            current_education_level=data.get('current_education_level'),
            education_institution_name=data.get('education_institution_name'),
            course_field_of_study=data.get('course_field_of_study'),
            year_of_study=data.get('year_of_study'),
            workplace_organization=data.get('workplace_organization'),
            motivation=data.get('motivation'),
            skills_interests=data.get('skills_interests')
        )
        
        db.session.add(application)
        db.session.commit()
        
        return jsonify({
            'message': 'Champion application submitted successfully. An administrator will review your application.',
            'application_id': application.application_id,
            'status': 'Pending'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/admin/registrations', methods=['GET'])
@admin_required
def get_registrations():
    """Admin: Get all member registrations"""
    try:
        status = request.args.get('status', 'Pending')
        registrations = MemberRegistration.query.filter_by(status=status).all()
        
        return jsonify({
            'registrations': [{
                'registration_id': r.registration_id,
                'full_name': r.full_name,
                'email': r.email,
                'phone_number': r.phone_number,
                'username': r.username,
                'date_of_birth': r.date_of_birth.isoformat() if r.date_of_birth else None,
                'gender': r.gender,
                'county_sub_county': r.county_sub_county,
                'status': r.status,
                'submitted_at': r.submitted_at.isoformat(),
                'reviewed_at': r.reviewed_at.isoformat() if r.reviewed_at else None,
                'rejection_reason': r.rejection_reason
            } for r in registrations]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/admin/registrations/<int:registration_id>/approve', methods=['POST'])
@admin_required
def approve_registration(registration_id):
    """Admin: Approve a member registration"""
    try:
        registration = MemberRegistration.query.get_or_404(registration_id)
        
        if registration.status != 'Pending':
            return jsonify({'error': 'Registration already processed'}), 400
        
        # Create user account
        user = User(username=registration.username)
        user.set_role(User.ROLE_PREVENTION_ADVOCATE)  # Default role for new members
        user.password_hash = registration.password_hash  # Use the hashed password from registration
        
        db.session.add(user)
        db.session.flush()  # Get user_id
        
        # Update registration
        registration.status = 'Approved'
        registration.reviewed_at = datetime.utcnow()
        registration.reviewed_by = current_user.user_id
        registration.created_user_id = user.user_id
        
        db.session.commit()
        
        return jsonify({
            'message': 'Registration approved successfully',
            'user_id': user.user_id,
            'username': user.username
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/admin/registrations/<int:registration_id>/reject', methods=['POST'])
@admin_required
def reject_registration(registration_id):
    """Admin: Reject a member registration"""
    try:
        registration = MemberRegistration.query.get_or_404(registration_id)
        
        if registration.status != 'Pending':
            return jsonify({'error': 'Registration already processed'}), 400
        
        data = request.get_json()
        reason = data.get('reason', 'No reason provided')
        
        registration.status = 'Rejected'
        registration.reviewed_at = datetime.utcnow()
        registration.reviewed_by = current_user.user_id
        registration.rejection_reason = reason
        
        db.session.commit()
        
        return jsonify({
            'message': 'Registration rejected',
            'reason': reason
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/admin/champion-applications', methods=['GET'])
@admin_required
def get_champion_applications():
    """Admin: Get all champion applications"""
    try:
        status = request.args.get('status', 'Pending')
        applications = ChampionApplication.query.filter_by(status=status).all()
        
        return jsonify({
            'applications': [{
                'application_id': a.application_id,
                'user_id': a.user_id,
                'full_name': a.full_name,
                'email': a.email,
                'phone_number': a.phone_number,
                'gender': a.gender,
                'date_of_birth': a.date_of_birth.isoformat(),
                'county_sub_county': a.county_sub_county,
                'current_education_level': a.current_education_level,
                'education_institution_name': a.education_institution_name,
                'motivation': a.motivation,
                'skills_interests': a.skills_interests,
                'status': a.status,
                'submitted_at': a.submitted_at.isoformat(),
                'reviewed_at': a.reviewed_at.isoformat() if a.reviewed_at else None,
                'rejection_reason': a.rejection_reason
            } for a in applications]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/admin/champion-applications/<int:application_id>/approve', methods=['POST'])
@admin_required
def approve_champion_application(application_id):
    """Admin: Approve a champion application"""
    try:
        application = ChampionApplication.query.get_or_404(application_id)
        
        if application.status != 'Pending':
            return jsonify({'error': 'Application already processed'}), 400
        
        data = request.get_json()
        assigned_champion_code = data.get('assigned_champion_code')
        
        if not assigned_champion_code:
            return jsonify({'error': 'Champion code is required'}), 400
        
        # Check if champion code already exists
        if Champion.query.filter_by(assigned_champion_code=assigned_champion_code).first():
            return jsonify({'error': 'Champion code already exists'}), 400
        
        # Create champion profile
        champion = Champion(
            user_id=application.user_id,
            full_name=application.full_name,
            email=application.email,
            phone_number=application.phone_number,
            alternative_phone_number=application.alternative_phone_number,
            gender=application.gender,
            date_of_birth=application.date_of_birth,
            county_sub_county=application.county_sub_county,
            assigned_champion_code=assigned_champion_code,
            emergency_contact_name=application.emergency_contact_name,
            emergency_contact_relationship=application.emergency_contact_relationship,
            emergency_contact_phone=application.emergency_contact_phone,
            current_education_level=application.current_education_level,
            education_institution_name=application.education_institution_name,
            course_field_of_study=application.course_field_of_study,
            year_of_study=application.year_of_study,
            workplace_organization=application.workplace_organization,
            date_of_application=datetime.utcnow().date(),
            application_status='Recruited',
            champion_status='Active'
        )
        
        db.session.add(champion)
        db.session.flush()  # Get champion_id
        
        # Update user to link champion profile
        user = User.query.get(application.user_id)
        user.champion_id = champion.champion_id
        
        # Update application
        application.status = 'Approved'
        application.reviewed_at = datetime.utcnow()
        application.reviewed_by = current_user.user_id
        application.created_champion_id = champion.champion_id
        
        db.session.commit()
        
        return jsonify({
            'message': 'Champion application approved successfully',
            'champion_id': champion.champion_id,
            'champion_code': champion.assigned_champion_code
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/admin/champion-applications/<int:application_id>/reject', methods=['POST'])
@admin_required
def reject_champion_application(application_id):
    """Admin: Reject a champion application"""
    try:
        application = ChampionApplication.query.get_or_404(application_id)
        
        if application.status != 'Pending':
            return jsonify({'error': 'Application already processed'}), 400
        
        data = request.get_json()
        reason = data.get('reason', 'No reason provided')
        
        application.status = 'Rejected'
        application.reviewed_at = datetime.utcnow()
        application.reviewed_by = current_user.user_id
        application.rejection_reason = reason
        
        db.session.commit()
        
        return jsonify({
            'message': 'Champion application rejected',
            'reason': reason
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/affirmations', methods=['GET'])
def api_list_affirmations():
    try:
        affirmations = DailyAffirmation.query.filter_by(active=True).order_by(DailyAffirmation.scheduled_date.asc().nullsfirst()).all()
        return jsonify({'affirmations': [a.to_dict() for a in affirmations]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/symbolic-items', methods=['GET'])
def api_list_symbolic_items():
    try:
        items = SymbolicItem.query.order_by(SymbolicItem.item_name.asc()).all()
        return jsonify({'items': [i.to_dict() for i in items]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/assessments', methods=['GET'])
def api_list_assessments():
    try:
        # Return recent assessments (privacy: no raw scores)
        q = MentalHealthAssessment.query.order_by(MentalHealthAssessment.assessment_date.desc()).limit(50).all()
        def serialize(a):
            return {
                'assessment_id': a.assessment_id,
                'champion_code': a.champion_code,
                'assessment_type': a.assessment_type,
                'assessment_date': a.assessment_date.isoformat() if a.assessment_date else None,
                'risk_category': a.risk_category,
                'notes': a.notes,
            }
        return jsonify({'assessments': [serialize(x) for x in q]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/media-galleries', methods=['GET'])
def api_list_media_galleries():
    try:
        galleries = MediaGallery.query.filter_by(published=True).order_by(MediaGallery.published_at.desc()).all()
        return jsonify({'galleries': [g.to_dict() for g in galleries]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/toolkit', methods=['GET'])
def api_list_toolkit():
    try:
        items = InstitutionalToolkitItem.query.filter_by(published=True).order_by(InstitutionalToolkitItem.created_at.desc()).all()
        return jsonify({'toolkit': [i.to_dict() for i in items]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/umv-global', methods=['GET'])
def api_list_umv_global():
    try:
        entries = UMVGlobalEntry.query.order_by(UMVGlobalEntry.key.asc()).all()
        return jsonify({'entries': [e.to_dict() for e in entries]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/resources', methods=['GET'])
def api_list_resources():
    try:
        resources = ResourceItem.query.filter_by(published=True).order_by(ResourceItem.published_at.desc()).all()
        return jsonify({'resources': [r.to_dict() for r in resources]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/stories', methods=['GET'])
def api_list_stories():
    try:
        stories = BlogPost.query.filter_by(category='Success Stories', published=True).order_by(BlogPost.published_at.desc()).all()
        return jsonify({'stories': [s.to_dict() for s in stories]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@public_auth_bp.route('/api/my-applications', methods=['GET'])
@login_required
def get_my_applications():
    """Get current user's champion applications"""
    try:
        applications = ChampionApplication.query.filter_by(user_id=current_user.user_id).all()
        
        return jsonify({
            'applications': [{
                'application_id': a.application_id,
                'full_name': a.full_name,
                'status': a.status,
                'submitted_at': a.submitted_at.isoformat(),
                'reviewed_at': a.reviewed_at.isoformat() if a.reviewed_at else None,
                'rejection_reason': a.rejection_reason
            } for a in applications]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# CHAMPION SELF-REGISTRATION - PRIVACY-FIRST
# For frontend member portal
# ============================================================================

@public_auth_bp.route('/api/champions/register', methods=['POST'])
def register_champion():
    """
    Public endpoint for champion self-registration.
    Generates unique champion code (UMV-YYYY-NNNNNN).
    Does NOT create User account - champions register first, then can create account later.
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = [
            'full_name', 'gender', 'date_of_birth', 'phone_number',
            'county_sub_county', 'consent_obtained'
        ]
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Validate consent
        if not data.get('consent_obtained'):
            return jsonify({
                'success': False,
                'error': 'Consent must be obtained before registration'
            }), 400
        
        # Validate email format if provided (email is optional)
        if data.get('email'):
            if not validate_email(data['email']):
                return jsonify({
                    'success': False,
                    'error': 'Invalid email format'
                }), 400
        
        # Validate phone number
        if not validate_phone(data['phone_number']):
            return jsonify({
                'success': False,
                'error': 'Invalid phone number format. Use 254XXXXXXXXX or 07XXXXXXXX'
            }), 400
        
        # Check for duplicate phone (always) and email (only if provided)
        filters = [Champion.phone_number == data['phone_number']]
        if data.get('email'):
            filters.append(Champion.email == data['email'])

        existing = Champion.query.filter(sa.or_(*filters)).first()
        if existing:
            return jsonify({
                'success': False,
                'error': 'A champion with this email or phone number already exists'
            }), 409
        
        # Generate unique champion code
        from models import generate_champion_code
        champion_code = generate_champion_code()
        
        # Parse date of birth
        try:
            dob = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid date format for date_of_birth. Use YYYY-MM-DD'
            }), 400
        
        # Create champion record
        new_champion = Champion(
            full_name=data['full_name'],
            gender=data['gender'],
            date_of_birth=dob,
            phone_number=data['phone_number'],
            alternative_phone_number=data.get('alternative_phone_number'),
            email=data.get('email'),
            county_sub_county=data['county_sub_county'],
            assigned_champion_code=champion_code,
            
            # Emergency contacts (optional)
            emergency_contact_name=data.get('emergency_contact_name'),
            emergency_contact_relationship=data.get('emergency_contact_relationship'),
            emergency_contact_phone=data.get('emergency_contact_phone'),
            
            # Education (optional)
            current_education_level=data.get('current_education_level'),
            education_institution_name=data.get('education_institution_name'),
            course_field_of_study=data.get('course_field_of_study'),
            year_of_study=data.get('year_of_study'),
            workplace_organization=data.get('workplace_organization'),
            
            # Program enrollment
            date_of_application=date.today(),
            recruitment_source=data.get('recruitment_source', 'Online Registration'),
            application_status='Pending',
            champion_status='Active',
            
            # Consent
            consent_obtained=True,
            consent_date=date.today(),
            institution_name=data.get('institution_name'),
            institution_consent_obtained=data.get('institution_consent_obtained', False),
            
            # Initialize risk level
            risk_level='Low'
        )
        
        db.session.add(new_champion)
        db.session.commit()
        
        # IMPORTANT: Return champion_code to the user (they need this for assessments)
        return jsonify({
            'success': True,
            'message': 'Champion registered successfully',
            'champion_code': champion_code,
            'champion_id': new_champion.champion_id,
            'important_notice': 'Please save your Champion Code securely. You will need it for all future interactions.'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Registration failed: {str(e)}'
        }), 500


@public_auth_bp.route('/api/champions/verify-code', methods=['POST'])
def verify_champion_code():
    """
    Verify a champion code exists (public endpoint for verification).
    Does NOT return champion details for privacy.
    """
    data = request.get_json()
    champion_code = data.get('champion_code', '').strip().upper()
    
    if not champion_code:
        return jsonify({
            'success': False,
            'valid': False,
            'message': 'Champion code is required'
        }), 400
    
    champion = Champion.query.filter_by(assigned_champion_code=champion_code).first()
    
    return jsonify({
        'success': True,
        'valid': bool(champion),
        'message': 'Champion code is valid' if champion else 'Invalid champion code'
    }), 200
