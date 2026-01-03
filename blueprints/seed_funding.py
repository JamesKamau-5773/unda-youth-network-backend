"""
Seed Funding API Blueprint
Handles seed funding applications for Campus Edition workstream
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, SeedFundingApplication, User
from datetime import datetime
from decorators import admin_required

seed_funding_bp = Blueprint('seed_funding', __name__, url_prefix='/api/seed-funding')


@seed_funding_bp.route('/apply', methods=['POST'])
@login_required
def submit_application():
    """Submit a new seed funding application"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['applicant_name', 'email', 'phone_number', 'project_title', 
                          'project_description', 'total_budget_requested']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Parse dates if provided
        project_start_date = None
        project_end_date = None
        
        if data.get('project_start_date'):
            try:
                project_start_date = datetime.strptime(data['project_start_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid project start date format. Use YYYY-MM-DD'}), 400
        
        if data.get('project_end_date'):
            try:
                project_end_date = datetime.strptime(data['project_end_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid project end date format. Use YYYY-MM-DD'}), 400
        
        # Create new application
        application = SeedFundingApplication(
            user_id=current_user.user_id,
            applicant_name=data['applicant_name'],
            email=data['email'],
            phone_number=data['phone_number'],
            institution_name=data.get('institution_name'),
            student_id_number=data.get('student_id_number'),
            project_title=data['project_title'],
            project_description=data['project_description'],
            project_category=data.get('project_category'),
            target_beneficiaries=data.get('target_beneficiaries'),
            expected_impact=data.get('expected_impact'),
            total_budget_requested=data['total_budget_requested'],
            budget_breakdown=data.get('budget_breakdown', []),
            other_funding_sources=data.get('other_funding_sources'),
            project_start_date=project_start_date,
            project_end_date=project_end_date,
            implementation_timeline=data.get('implementation_timeline'),
            proposal_document_url=data.get('proposal_document_url'),
            budget_document_url=data.get('budget_document_url'),
            team_members=data.get('team_members', []),
            team_size=data.get('team_size'),
            status='Pending'
        )
        
        db.session.add(application)
        db.session.commit()
        
        return jsonify({
            'message': 'Seed funding application submitted successfully',
            'application': application.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@seed_funding_bp.route('/my-applications', methods=['GET'])
@login_required
def get_my_applications():
    """Get all applications submitted by the current user"""
    try:
        applications = SeedFundingApplication.query.filter_by(
            user_id=current_user.user_id
        ).order_by(SeedFundingApplication.submitted_at.desc()).all()
        
        return jsonify({
            'applications': [app.to_dict() for app in applications]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@seed_funding_bp.route('/applications/<int:application_id>', methods=['GET'])
@login_required
def get_application(application_id):
    """Get details of a specific application"""
    try:
        application = SeedFundingApplication.query.get_or_404(application_id)
        
        # Only allow user to view their own applications unless admin
        if application.user_id != current_user.user_id and current_user.role != 'Admin':
            return jsonify({'error': 'Unauthorized'}), 403
        
        return jsonify(application.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@seed_funding_bp.route('/applications', methods=['GET'])
@login_required
@admin_required
def list_all_applications():
    """List all seed funding applications (Admin only)"""
    try:
        status_filter = request.args.get('status', 'all')
        
        query = SeedFundingApplication.query
        
        if status_filter != 'all':
            query = query.filter_by(status=status_filter)
        
        applications = query.order_by(
            SeedFundingApplication.submitted_at.desc()
        ).all()
        
        # Get statistics
        stats = {
            'total': SeedFundingApplication.query.count(),
            'pending': SeedFundingApplication.query.filter_by(status='Pending').count(),
            'under_review': SeedFundingApplication.query.filter_by(status='Under Review').count(),
            'approved': SeedFundingApplication.query.filter_by(status='Approved').count(),
            'rejected': SeedFundingApplication.query.filter_by(status='Rejected').count(),
            'funded': SeedFundingApplication.query.filter_by(status='Funded').count()
        }
        
        return jsonify({
            'applications': [app.to_dict() for app in applications],
            'stats': stats
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@seed_funding_bp.route('/applications/<int:application_id>/update-status', methods=['POST'])
@login_required
@admin_required
def update_application_status(application_id):
    """Update application status (Admin only)"""
    try:
        application = SeedFundingApplication.query.get_or_404(application_id)
        data = request.get_json()
        
        new_status = data.get('status')
        if not new_status:
            return jsonify({'error': 'Status is required'}), 400
        
        valid_statuses = ['Pending', 'Under Review', 'Approved', 'Rejected', 'Funded']
        if new_status not in valid_statuses:
            return jsonify({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400
        
        application.status = new_status
        application.reviewed_at = datetime.utcnow()
        application.reviewed_by = current_user.user_id
        
        # Handle approval
        if new_status == 'Approved':
            application.approved_amount = data.get('approved_amount', application.total_budget_requested)
            application.approval_conditions = data.get('approval_conditions')
        
        # Handle rejection
        if new_status == 'Rejected':
            application.rejection_reason = data.get('rejection_reason')
        
        # Handle funding disbursement
        if new_status == 'Funded':
            if data.get('disbursement_date'):
                try:
                    application.disbursement_date = datetime.strptime(
                        data['disbursement_date'], '%Y-%m-%d'
                    ).date()
                except ValueError:
                    return jsonify({'error': 'Invalid disbursement date format'}), 400
            
            application.disbursement_method = data.get('disbursement_method')
            application.disbursement_reference = data.get('disbursement_reference')
        
        # Update admin notes
        if data.get('admin_notes'):
            application.admin_notes = data['admin_notes']
        
        db.session.commit()
        
        return jsonify({
            'message': f'Application status updated to {new_status}',
            'application': application.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@seed_funding_bp.route('/statistics', methods=['GET'])
@login_required
@admin_required
def get_statistics():
    """Get seed funding statistics (Admin only)"""
    try:
        from sqlalchemy import func
        
        stats = {
            'total_applications': SeedFundingApplication.query.count(),
            'pending': SeedFundingApplication.query.filter_by(status='Pending').count(),
            'under_review': SeedFundingApplication.query.filter_by(status='Under Review').count(),
            'approved': SeedFundingApplication.query.filter_by(status='Approved').count(),
            'rejected': SeedFundingApplication.query.filter_by(status='Rejected').count(),
            'funded': SeedFundingApplication.query.filter_by(status='Funded').count(),
            'total_amount_requested': db.session.query(
                func.sum(SeedFundingApplication.total_budget_requested)
            ).scalar() or 0,
            'total_amount_approved': db.session.query(
                func.sum(SeedFundingApplication.approved_amount)
            ).filter(
                SeedFundingApplication.status.in_(['Approved', 'Funded'])
            ).scalar() or 0,
            'total_amount_disbursed': db.session.query(
                func.sum(SeedFundingApplication.approved_amount)
            ).filter_by(status='Funded').scalar() or 0
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
