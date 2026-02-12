"""
Support Review API Blueprint
Receives partnership inquiry, volunteer, and host-event form submissions from the frontend.
"""
from flask import Blueprint, request, jsonify, current_app
from models import db
from services.support_review_service import (
    create_partnership_inquiry,
    create_volunteer_submission,
    create_host_submission,
)
import re

support_review_bp = Blueprint('support_review', __name__, url_prefix='/api/support-review')

EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


@support_review_bp.route('/partnership', methods=['POST'])
def submit_partnership_inquiry():
    """
    Receive partnership inquiry form data from the frontend.
    Expected JSON payload:
      { organizationName, contactPerson, email, partnershipType, message }
    """
    try:
        data = request.get_json(silent=True) or {}

        required = ['organizationName', 'contactPerson', 'email', 'partnershipType', 'message']
        missing = [f for f in required if not data.get(f, '').strip()]
        if missing:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing)}'
            }), 400

        if not EMAIL_RE.match(data['email'].strip()):
            return jsonify({'success': False, 'error': 'Invalid email address'}), 400

        inquiry = create_partnership_inquiry(data)
        current_app.logger.info(f'Partnership inquiry received from {inquiry.organization_name}')

        return jsonify({
            'success': True,
            'message': 'Partnership inquiry submitted successfully. We will get back to you within 48 hours.',
            'inquiry': inquiry.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Error processing partnership inquiry')
        return jsonify({'success': False, 'error': 'An unexpected error occurred. Please try again.'}), 500


@support_review_bp.route('/support', methods=['POST'])
def submit_support_event():
    """
    Receive volunteer / host-event form data from the frontend.
    Expected JSON payload:
      { type: 'volunteer' | 'host-event', name, email, phone?, interest, motivation? }
    """
    try:
        data = request.get_json(silent=True) or {}

        submission_type = data.get('type', '').strip()
        if submission_type not in ('volunteer', 'host-event'):
            return jsonify({
                'success': False,
                'error': 'Invalid submission type. Must be "volunteer" or "host-event".'
            }), 400

        required = ['name', 'email', 'interest']
        missing = [f for f in required if not data.get(f, '').strip()]
        if missing:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing)}'
            }), 400

        if not EMAIL_RE.match(data['email'].strip()):
            return jsonify({'success': False, 'error': 'Invalid email address'}), 400

        if submission_type == 'volunteer':
            submission = create_volunteer_submission(data)
            label = 'Support application'
        else:
            submission = create_host_submission(data)
            label = 'Event hosting request'

        current_app.logger.info(f'{label} received from {submission.full_name}')

        return jsonify({
            'success': True,
            'message': f'{label} submitted successfully. We will get back to you within 48 hours.',
            'submission': submission.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Error processing support/event submission')
        return jsonify({'success': False, 'error': 'An unexpected error occurred. Please try again.'}), 500
