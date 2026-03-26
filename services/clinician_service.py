"""Clinician Service Layer

Handles all business logic for clinician registration, verification, and management.
Implements SOLID principles and separates concerns from routes.
"""

from datetime import datetime, date, timezone, timedelta
from typing import Optional, Dict, List
from models import (
    db, User, ClinicianProfile, ClinicianSpecialization, ClinicianLanguage,
    ClinicianAuditLog, YouthClinicianReferral, ClinicalSession
)
from flask import current_app, request


class ClinicianService:
    """Service layer for clinician onboarding, verification, and management."""
    
    # CONSTANTS
    VERIFICATION_STATUS_PENDING = 'pending_verification'
    VERIFICATION_STATUS_UNDER_REVIEW = 'under_admin_review'
    VERIFICATION_STATUS_VERIFIED = 'verified'
    VERIFICATION_STATUS_REJECTED = 'rejected'
    VERIFICATION_STATUS_LICENSE_EXPIRED = 'license_expired'
    
    REFERRAL_STATUS_PENDING = 'pending'
    REFERRAL_STATUS_ACCEPTED = 'accepted'
    REFERRAL_STATUS_COMPLETED = 'completed'
    REFERRAL_STATUS_CANCELLED = 'cancelled'
    
    @staticmethod
    def register_clinician(form_data: Dict, client_ip: str) -> Dict:
        """Register a new clinician. Defaults to pending_verification state.
        
        Args:
            form_data: Dict containing:
                - license_number (required, unique)
                - regulatory_body (required)
                - license_expiry_date (required, ISO format YYYY-MM-DD)
                - professional_title (required)
                - professional_indemnity_insurance_provider (required)
                - insurance_policy_number (optional)
                - insurance_expiry_date (optional, ISO format)
                - emergency_contact_name (required)
                - emergency_contact_phone (required)
                - emergency_contact_relationship (optional)
                - years_of_practice (optional)
                - service_mode (required: 'In-person', 'Telehealth', 'Hybrid')
                - specializations (optional, list of strings)
                - languages (optional, list of dicts with 'name' and 'proficiency_level')
                - declaration_accepted (required, boolean)
                - username (required)
                - password (required)
            client_ip: Client IP address for audit trail
        
        Returns:
            Dict with clinician_id, user_id, and status message
        
        Raises:
            ValueError: If validation fails
        """
        # Validate required fields
        required_fields = [
            'license_number', 'regulatory_body', 'license_expiry_date',
            'professional_title', 'professional_indemnity_insurance_provider',
            'emergency_contact_name', 'emergency_contact_phone',
            'service_mode', 'username', 'password', 'declaration_accepted'
        ]
        
        for field in required_fields:
            if field not in form_data or not form_data.get(field):
                raise ValueError(f"'{field}' is required")
        
        # Validate license expiry date is in future
        try:
            license_expiry = datetime.strptime(form_data['license_expiry_date'], '%Y-%m-%d').date()
            if license_expiry < date.today():
                raise ValueError("License expiry date must be in the future")
        except ValueError as e:
            if 'time data' in str(e):
                raise ValueError("Invalid license_expiry_date format. Use YYYY-MM-DD")
            raise
        
        # Validate service_mode
        valid_modes = ['In-person', 'Telehealth', 'Hybrid']
        if form_data['service_mode'] not in valid_modes:
            raise ValueError(f"Service mode must be one of: {', '.join(valid_modes)}")
        
        # Validate declaration acceptance
        if not form_data.get('declaration_accepted'):
            raise ValueError("You must accept the declaration to proceed")
        
        # Check if license already exists
        existing_license = ClinicianProfile.query.filter_by(
            license_number=form_data['license_number']
        ).first()
        if existing_license:
            raise ValueError(f"License number {form_data['license_number']} is already registered")
        
        # Create User account
        try:
            user = User(username=form_data['username'])
            user.set_password(form_data['password'])
            user.set_role(User.ROLE_CLINICIAN)  # Set role to Clinician
            user.email = form_data.get('email')  # Optional
            
            db.session.add(user)
            db.session.flush()  # Get user_id without committing
            
        except Exception as e:
            db.session.rollback()
            if 'already exists' in str(e).lower() or 'unique' in str(e).lower():
                raise ValueError(f"Username '{form_data['username']}' already exists")
            raise ValueError(f"Failed to create user account: {str(e)}")
        
        # Create ClinicianProfile
        try:
            clinician = ClinicianProfile(
                user_id=user.user_id,
                license_number=form_data['license_number'],
                regulatory_body=form_data['regulatory_body'],
                license_expiry_date=license_expiry,
                professional_title=form_data['professional_title'],
                professional_indemnity_insurance_provider=form_data['professional_indemnity_insurance_provider'],
                insurance_policy_number=form_data.get('insurance_policy_number'),
                emergency_contact_name=form_data['emergency_contact_name'],
                emergency_contact_phone=form_data['emergency_contact_phone'],
                emergency_contact_relationship=form_data.get('emergency_contact_relationship'),
                years_of_practice=form_data.get('years_of_practice'),
                service_mode=form_data['service_mode'],
                supervision_history=form_data.get('supervision_history'),
                supervision_provider_name=form_data.get('supervision_provider_name'),
                declaration_accepted=True,
                declaration_timestamp=datetime.now(timezone.utc),
                declaration_ip_address=client_ip,
                verification_status=ClinicianService.VERIFICATION_STATUS_PENDING
            )
            
            # Parse and add insurance expiry date if provided
            if form_data.get('insurance_expiry_date'):
                try:
                    clinician.insurance_expiry_date = datetime.strptime(
                        form_data['insurance_expiry_date'], '%Y-%m-%d'
                    ).date()
                except ValueError:
                    current_app.logger.warning("Invalid insurance_expiry_date format; skipping")
            
            db.session.add(clinician)
            db.session.flush()
            
            # Add specializations
            for spec in form_data.get('specializations', []):
                if spec:  # Skip empty strings
                    specialization = ClinicianSpecialization(
                        clinician_id=clinician.clinician_id,
                        specialization=spec.strip()
                    )
                    db.session.add(specialization)
            
            # Add languages
            for lang_data in form_data.get('languages', []):
                if isinstance(lang_data, dict) and lang_data.get('name'):
                    language = ClinicianLanguage(
                        clinician_id=clinician.clinician_id,
                        language=lang_data['name'].strip(),
                        proficiency_level=lang_data.get('proficiency_level', 'Intermediate')
                    )
                    db.session.add(language)
            
            # Commit all changes
            db.session.commit()
            
            # Log application submission
            ClinicianService._log_action(
                clinician.clinician_id,
                'application_submitted',
                None,
                f'Clinician registered: {clinician.professional_title}'
            )
            
            return {
                'success': True,
                'clinician_id': clinician.clinician_id,
                'user_id': user.user_id,
                'message': 'Registration successful. Pending admin verification.'
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to create clinician profile: {str(e)}")
            raise ValueError(f"Failed to create clinician profile: {str(e)}")
    
    @staticmethod
    def verify_clinician(clinician_id: int, admin_user_id: int, approved: bool, notes: str = '') -> Dict:
        """Admin approval/rejection workflow.
        
        Args:
            clinician_id: ID of clinician to verify
            admin_user_id: ID of admin performing verification
            approved: True to approve, False to reject
            notes: Additional notes/reason
        
        Returns:
            Dict with updated clinician data
        
        Raises:
            ValueError: If clinician not found
        """
        clinician = ClinicianProfile.query.get(clinician_id)
        if not clinician:
            raise ValueError(f"Clinician {clinician_id} not found")
        
        try:
            if approved:
                clinician.verification_status = ClinicianService.VERIFICATION_STATUS_VERIFIED
                clinician.verified_by_user_id = admin_user_id
                clinician.verified_date = datetime.now(timezone.utc)
                clinician.user.role = User.ROLE_CLINICIAN
                
                action_msg = 'Clinician verified and granted platform access'
                action = 'verified'
            else:
                clinician.verification_status = ClinicianService.VERIFICATION_STATUS_REJECTED
                clinician.verified_by_user_id = admin_user_id
                clinician.verified_date = datetime.now(timezone.utc)
                clinician.verification_notes = notes
                
                action_msg = f'Clinician registration rejected: {notes}'
                action = 'rejected'
            
            db.session.commit()
            
            # Log action
            ClinicianService._log_action(clinician_id, action, admin_user_id, action_msg)
            
            return {
                'success': True,
                'clinician_id': clinician_id,
                'verification_status': clinician.verification_status,
                'message': action_msg
            }
        
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to verify clinician {clinician_id}: {str(e)}")
            raise ValueError(f"Verification failed: {str(e)}")
    
    @staticmethod
    def is_license_expired(clinician: ClinicianProfile) -> bool:
        """Check if professional license has expired."""
        return clinician.license_expiry_date < date.today()
    
    @staticmethod
    def get_active_clinicians_for_specialization(
        specialization: str,
        service_mode: Optional[str] = None
    ) -> List[ClinicianProfile]:
        """Routing logic: Find available clinicians by specialization.
        
        Args:
            specialization: Required specialization (e.g., "Trauma Therapy")
            service_mode: Optional service mode filter ('In-person', 'Telehealth', 'Hybrid')
        
        Returns:
            List of matching clinicians available for referral
        """
        query = db.session.query(ClinicianProfile).join(
            ClinicianSpecialization
        ).filter(
            ClinicianSpecialization.specialization == specialization,
            ClinicianProfile.verification_status == ClinicianService.VERIFICATION_STATUS_VERIFIED,
            ClinicianProfile.account_suspended == False,
            ClinicianProfile.license_expiry_date >= date.today()
        )
        
        if service_mode:
            query = query.filter(ClinicianProfile.service_mode.contains(service_mode))
        
        return query.all()
    
    @staticmethod
    def get_pending_clinicians() -> List[ClinicianProfile]:
        """Get all clinicians pending admin verification."""
        return ClinicianProfile.query.filter_by(
            verification_status=ClinicianService.VERIFICATION_STATUS_PENDING
        ).order_by(ClinicianProfile.created_at.desc()).all()
    
    @staticmethod
    def suspend_clinician(clinician_id: int, reason: str, admin_user_id: int) -> Dict:
        """Suspend clinician account (e.g., due to expired license or misconduct).
        
        Args:
            clinician_id: ID of clinician to suspend
            reason: Reason for suspension
            admin_user_id: ID of admin performing suspension
        
        Returns:
            Dict with success status
        
        Raises:
            ValueError: If clinician not found
        """
        clinician = ClinicianProfile.query.get(clinician_id)
        if not clinician:
            raise ValueError(f"Clinician {clinician_id} not found")
        
        try:
            clinician.account_suspended = True
            clinician.suspension_reason = reason
            db.session.commit()
            
            # Log suspension
            ClinicianService._log_action(
                clinician_id,
                'suspended',
                admin_user_id,
                f'Account suspended: {reason}'
            )
            
            return {
                'success': True,
                'clinician_id': clinician_id,
                'message': f'Clinician suspended: {reason}'
            }
        
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Suspension failed: {str(e)}")
    
    @staticmethod
    def check_expired_licenses() -> Dict:
        """Scheduled job: Auto-suspend clinicians with expired licenses.
        
        Called by Celery scheduled task (Phase 3).
        
        Returns:
            Dict with count of auto-suspended clinicians
        """
        expired_clinicians = ClinicianProfile.query.filter(
            ClinicianProfile.license_expiry_date < date.today(),
            ClinicianProfile.account_suspended == False
        ).all()
        
        count = 0
        for clinician in expired_clinicians:
            try:
                clinician.account_suspended = True
                clinician.suspension_reason = 'License expired'
                clinician.verification_status = ClinicianService.VERIFICATION_STATUS_LICENSE_EXPIRED
                db.session.add(clinician)
                
                ClinicianService._log_action(
                    clinician.clinician_id,
                    'license_expired',
                    None,
                    f'License expired on {clinician.license_expiry_date}. Account auto-suspended.'
                )
                count += 1
            except Exception as e:
                current_app.logger.error(f"Failed to process expired license for clinician {clinician.clinician_id}: {str(e)}")
        
        db.session.commit()
        return {'suspended_count': count}
    
    @staticmethod
    def create_referral(
        clinician_id: int,
        prevention_advocate_id: int,
        youth_id: int,
        referral_reason: str,
        notes: str = ''
    ) -> Dict:
        """Create a referral from Prevention Advocate to Clinician.
        
        Args:
            clinician_id: Target clinician
            prevention_advocate_id: Referring prevention advocate
            youth_id: Youth being referred
            referral_reason: Why is this youth being referred?
            notes: Additional notes
        
        Returns:
            Dict with referral_id and status
        
        Raises:
            ValueError: If clinician not found or not active
        """
        clinician = ClinicianProfile.query.get(clinician_id)
        if not clinician:
            raise ValueError(f"Clinician {clinician_id} not found")
        
        if not clinician.is_active():
            raise ValueError("Clinician is not available for referrals (not verified, suspended, or license expired)")
        
        try:
            referral = YouthClinicianReferral(
                clinician_id=clinician_id,
                referring_prevention_advocate_id=prevention_advocate_id,
                youth_id=youth_id,
                status=ClinicianService.REFERRAL_STATUS_PENDING,
                referral_reason=referral_reason,
                notes=notes
            )
            
            db.session.add(referral)
            db.session.commit()
            
            return {
                'success': True,
                'referral_id': referral.referral_id,
                'status': 'pending'
            }
        
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Failed to create referral: {str(e)}")
    
    @staticmethod
    def _log_action(
        clinician_id: int,
        action: str,
        performed_by_user_id: Optional[int],
        notes: str = ''
    ) -> None:
        """Internal: Log clinician action to audit trail.
        
        Args:
            clinician_id: ID of clinician
            action: Action type (e.g., 'verified', 'rejected', 'suspended')
            performed_by_user_id: ID of user performing action (None for system actions)
            notes: Additional context
        """
        try:
            audit_log = ClinicianAuditLog(
                clinician_id=clinician_id,
                action=action,
                performed_by_user_id=performed_by_user_id,
                notes=notes
            )
            db.session.add(audit_log)
            db.session.commit()
        except Exception as e:
            current_app.logger.error(f"Failed to log action '{action}' for clinician {clinician_id}: {str(e)}")


# Utility functions for Flask views

def get_clinician_or_404(clinician_id: int) -> ClinicianProfile:
    """Get clinician by ID or raise 404."""
    clinician = ClinicianProfile.query.get(clinician_id)
    if not clinician:
        from flask import abort
        abort(404)
    return clinician


def require_clinician_verified(clinician: ClinicianProfile) -> bool:
    """Check if clinician is verified. Used in guards."""
    return clinician.verification_status == ClinicianService.VERIFICATION_STATUS_VERIFIED
