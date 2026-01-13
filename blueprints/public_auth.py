from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, User, Champion, MemberRegistration, ChampionApplication
from decorators import admin_required
from password_validator import validate_password_strength
from datetime import datetime, date
import re

public_auth_bp = Blueprint('public_auth', __name__)


def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_phone(phone):
    """Validate Kenya phone number format"""
    # Remove spaces and special characters
    phone = re.sub(r'[\s\-\(\)]', '', phone)
    # Check if it matches Kenya phone format (254XXXXXXXXX or 07XXXXXXXX or 01XXXXXXXX)
    pattern = r'^(254[17]\d{8}|0[17]\d{8})$'
    return re.match(pattern, phone) is not None


@public_auth_bp.route('/api/auth/register', methods=['POST'])
def register_member():
    """Public endpoint for member registration"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['full_name', 'email', 'phone_number', 'username', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate email format
        if not validate_email(data['email']):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate phone number
        if not validate_phone(data['phone_number']):
            return jsonify({'error': 'Invalid phone number format. Use 254XXXXXXXXX or 07XXXXXXXX'}), 400
        
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
        
        # Check for existing email
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
            email=data['email'],
            phone_number=data['phone_number'],
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
        
        # Validate required fields
        required_fields = ['full_name', 'email', 'phone_number', 'gender', 'date_of_birth']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate email
        if not validate_email(data['email']):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate phone
        if not validate_phone(data['phone_number']):
            return jsonify({'error': 'Invalid phone number format'}), 400
        
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
            email=data['email'],
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
            'full_name', 'gender', 'date_of_birth', 'phone_number', 'email',
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
        
        # Validate email format
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
        
        # Check for duplicate email or phone
        existing = Champion.query.filter(
            (Champion.email == data['email']) | 
            (Champion.phone_number == data['phone_number'])
        ).first()
        
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
            email=data['email'],
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
