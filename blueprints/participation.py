from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from models import db, EventParticipation, Event, Champion
from decorators import supervisor_required
from datetime import datetime, timezone
import traceback

participation_bp = Blueprint('participation', __name__, url_prefix='/api/event-participation')


@participation_bp.route('/', methods=['GET'])
@login_required
@supervisor_required
def list_participations():
    """Get all event participations with optional filtering."""
    event_id = request.args.get('event_id', type=int)
    champion_id = request.args.get('champion_id', type=int)
    status = request.args.get('status')  # registered, confirmed, attended, cancelled
    
    query = EventParticipation.query
    
    if event_id:
        query = query.filter_by(event_id=event_id)
    if champion_id:
        query = query.filter_by(champion_id=champion_id)
    if status:
        query = query.filter_by(registration_status=status)
    
    query = query.order_by(EventParticipation.registered_at.desc())
    participations = query.all()
    
    return jsonify({
        'success': True,
        'total': len(participations),
        'participations': [{
            'participation_id': p.participation_id,
            'event_id': p.event_id,
            'event_title': p.event.title if p.event else None,
            'champion_id': p.champion_id,
            'champion_name': p.champion.full_name if p.champion else None,
            'registration_status': p.registration_status,
            'attended': p.attended,
            'attendance_confirmed_at': p.attendance_confirmed_at.isoformat() if p.attendance_confirmed_at else None,
            'feedback_score': p.feedback_score,
            'certificate_issued': p.certificate_issued,
            'registered_at': p.registered_at.isoformat() if p.registered_at else None
        } for p in participations]
    }), 200


@participation_bp.route('/<int:participation_id>', methods=['GET'])
@login_required
@supervisor_required
def get_participation(participation_id):
    """Get detailed participation record."""
    participation = db.session.get(EventParticipation, participation_id)
    if not participation:
        return jsonify({'success': False, 'message': 'Participation not found'}), 404
    
    return jsonify({
        'success': True,
        'participation': {
            'participation_id': participation.participation_id,
            'event_id': participation.event_id,
            'event_title': participation.event.title if participation.event else None,
            'event_date': participation.event.event_date.isoformat() if participation.event and participation.event.event_date else None,
            'champion_id': participation.champion_id,
            'champion_name': participation.champion.full_name if participation.champion else None,
            'registration_status': participation.registration_status,
            'attended': participation.attended,
            'attendance_confirmed_at': participation.attendance_confirmed_at.isoformat() if participation.attendance_confirmed_at else None,
            'feedback_score': participation.feedback_score,
            'feedback_comments': participation.feedback_comments,
            'certificate_issued': participation.certificate_issued,
            'registered_at': participation.registered_at.isoformat() if participation.registered_at else None
        }
    }), 200


@participation_bp.route('/', methods=['POST'])
@login_required
def register_for_event():
    """Register a champion for an event."""
    try:
        current_app.logger.info(f'Event participation registration request from user {current_user.user_id}')
        
        try:
            data = request.get_json()
            if not data:
                current_app.logger.warning('No JSON data in event participation request')
                return jsonify({
                    'success': False,
                    'message': 'Request body must be valid JSON'
                }), 400
        except Exception as json_error:
            current_app.logger.error(f'Error parsing JSON in event participation request: {str(json_error)}')
            return jsonify({
                'success': False,
                'message': 'Invalid JSON in request'
            }), 400
        
        required_fields = ['event_id', 'champion_id']
        missing_fields = [f for f in required_fields if f not in data]
        if missing_fields:
            current_app.logger.warning(f'Missing required fields in event participation: {missing_fields}')
            return jsonify({
                'success': False,
                'message': f'Missing required fields: {missing_fields}'
            }), 400
        
        # Validate event and champion exist
        try:
            event = db.session.get(Event, data['event_id'])
            champion = db.session.get(Champion, data['champion_id'])
            
            if not event:
                current_app.logger.warning(f'Event not found: event_id={data["event_id"]}')
            if not champion:
                current_app.logger.warning(f'Champion not found: champion_id={data["champion_id"]}')
            
            if not event or not champion:
                return jsonify({
                    'success': False,
                    'message': 'Event or Champion not found'
                }), 404
        except Exception as lookup_error:
            current_app.logger.error(f'Error looking up event/champion: {str(lookup_error)}')
            current_app.logger.error(f'Exception type: {type(lookup_error).__name__}')
            current_app.logger.error(f'Traceback: {traceback.format_exc()}')
            return jsonify({
                'success': False,
                'message': 'Error validating event and champion'
            }), 500
        
        # Check if already registered
        try:
            existing = EventParticipation.query.filter_by(
                event_id=data['event_id'],
                champion_id=data['champion_id']
            ).first()
            
            if existing:
                current_app.logger.info(f'Champion {data["champion_id"]} already registered for event {data["event_id"]}')
                return jsonify({
                    'success': False,
                    'message': 'Champion already registered for this event',
                    'participation_id': existing.participation_id
                }), 409
        except Exception as check_error:
            current_app.logger.error(f'Error checking existing registration: {str(check_error)}')
            return jsonify({
                'success': False,
                'message': 'Error checking registration status'
            }), 500
        
        # Check event capacity if applicable
        try:
            if event.max_participants:
                registered_count = EventParticipation.query.filter_by(
                    event_id=data['event_id'],
                    registration_status='Registered'
                ).count()
                
                if registered_count >= event.max_participants:
                    current_app.logger.info(f'Event {data["event_id"]} at full capacity')
                    return jsonify({
                        'success': False,
                        'message': 'Event is at full capacity'
                    }), 400
        except Exception as capacity_error:
            current_app.logger.error(f'Error checking event capacity: {str(capacity_error)}')
            return jsonify({
                'success': False,
                'message': 'Error checking event capacity'
            }), 500
        
        try:
            participation = EventParticipation(
                event_id=data['event_id'],
                champion_id=data['champion_id'],
                registration_status=data.get('registration_status', 'Registered')
            )
            
            db.session.add(participation)
            db.session.commit()
            
            current_app.logger.info(f'Event participation registered: participation_id={participation.participation_id}, event_id={data["event_id"]}, champion_id={data["champion_id"]}')
            return jsonify({
                'success': True,
                'message': 'Registration successful',
                'participation_id': participation.participation_id
            }), 201
        except Exception as create_error:
            db.session.rollback()
            error_msg = str(create_error)
            current_app.logger.error(f'Error creating event participation: {error_msg}')
            current_app.logger.error(f'Traceback: {traceback.format_exc()}')
            return jsonify({
                'success': False,
                'message': f'Error registering for event: {error_msg}'
            }), 500
            
    except Exception as e:
        import traceback
        error_msg = str(e)
        current_app.logger.error(f'Unexpected error in event participation registration: {error_msg}')
        current_app.logger.error(f'Traceback: {traceback.format_exc()}')
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred during registration'
        }), 500


@participation_bp.route('/<int:participation_id>/status', methods=['PUT'])
@login_required
@supervisor_required
def update_registration_status(participation_id):
    """Update registration status (confirm, cancel, etc.)."""
    participation = db.session.get(EventParticipation, participation_id)
    if not participation:
        return jsonify({'success': False, 'message': 'Participation not found'}), 404
    data = request.get_json()
    
    if not data.get('status'):
        return jsonify({
            'success': False,
            'message': 'Status is required'
        }), 400
    
    allowed_statuses = ['registered', 'confirmed', 'cancelled', 'waitlisted']
    if data['status'] not in allowed_statuses:
        return jsonify({
            'success': False,
            'message': f'Invalid status. Allowed: {allowed_statuses}'
        }), 400
    
    participation.registration_status = data['status']
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Registration status updated successfully'
    }), 200


@participation_bp.route('/<int:participation_id>/attendance', methods=['PUT'])
@login_required
@supervisor_required
def mark_attendance(participation_id):
    """Mark attendance for an event."""
    participation = db.session.get(EventParticipation, participation_id)
    if not participation:
        return jsonify({'success': False, 'message': 'Participation not found'}), 404
    data = request.get_json()
    
    if 'attended' not in data:
        return jsonify({
            'success': False,
            'message': 'attended field is required'
        }), 400
    
    participation.attended = data['attended']
    if data['attended']:
        participation.attendance_confirmed_at = datetime.now(timezone.utc)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Attendance updated successfully'
    }), 200


@participation_bp.route('/<int:participation_id>/feedback', methods=['PUT'])
@login_required
def submit_feedback(participation_id):
    """Submit feedback for an event."""
    participation = db.session.get(EventParticipation, participation_id)
    if not participation:
        return jsonify({'success': False, 'message': 'Participation not found'}), 404
    data = request.get_json()
    
    if 'feedback_score' in data:
        score = data['feedback_score']
        if not (1 <= score <= 5):
            return jsonify({
                'success': False,
                'message': 'Feedback score must be between 1 and 5'
            }), 400
        participation.feedback_score = score
    
    if 'feedback_comments' in data:
        participation.feedback_comments = data['feedback_comments']
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Feedback submitted successfully'
    }), 200


@participation_bp.route('/<int:participation_id>/certificate', methods=['POST'])
@login_required
@supervisor_required
def issue_certificate(participation_id):
    """Issue a certificate for event attendance."""
    participation = db.session.get(EventParticipation, participation_id)
    if not participation:
        return jsonify({'success': False, 'message': 'Participation not found'}), 404
    
    if not participation.attended:
        return jsonify({
            'success': False,
            'message': 'Cannot issue certificate: attendance not verified'
        }), 400
    
    if participation.certificate_issued:
        return jsonify({
            'success': False,
            'message': 'Certificate already issued',
            'issued_at': participation.certificate_issued_at.isoformat()
        }), 409
    
    participation.certificate_issued = True
    participation.certificate_issued_at = datetime.now(timezone.utc)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Certificate issued successfully',
        'issued_at': participation.certificate_issued_at.isoformat()
    }), 200


@participation_bp.route('/event/<int:event_id>/stats', methods=['GET'])
@login_required
@supervisor_required
def get_event_stats(event_id):
    """Get participation statistics for an event."""
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({'success': False, 'message': 'Event not found'}), 404
    
    participations = EventParticipation.query.filter_by(event_id=event_id).all()
    
    total_registered = len(participations)
    confirmed = sum(1 for p in participations if p.registration_status == 'Registered')
    attended = sum(1 for p in participations if p.attended)
    certificates_issued = sum(1 for p in participations if p.certificate_issued)
    
    feedbacks = [p.feedback_score for p in participations if p.feedback_score]
    avg_feedback = sum(feedbacks) / len(feedbacks) if feedbacks else None
    
    return jsonify({
        'success': True,
        'event_id': event_id,
        'event_title': event.title,
        'event_date': event.event_date.isoformat() if event.event_date else None,
        'stats': {
            'total_registered': total_registered,
            'confirmed': confirmed,
            'attended': attended,
            'attendance_rate': round(attended / confirmed * 100, 1) if confirmed > 0 else 0,
            'certificates_issued': certificates_issued,
            'average_feedback_score': round(avg_feedback, 2) if avg_feedback else None,
            'feedback_count': len(feedbacks)
        }
    }), 200


@participation_bp.route('/champion/<int:champion_id>/history', methods=['GET'])
@login_required
def get_champion_participation_history(champion_id):
    """Get participation history for a champion."""
    # Allow champions to view their own history, supervisors to view all
    if current_user.role not in ['Admin', 'Supervisor']:
        if not hasattr(current_user, 'champion') or current_user.champion.champion_id != champion_id:
            return jsonify({
                'success': False,
                'message': 'Unauthorized'
            }), 403
    
    participations = EventParticipation.query.filter_by(
        champion_id=champion_id
    ).order_by(EventParticipation.registered_at.desc()).all()
    
    return jsonify({
        'success': True,
        'champion_id': champion_id,
        'total_events': len(participations),
        'attended': sum(1 for p in participations if p.attended),
        'certificates_earned': sum(1 for p in participations if p.certificate_issued),
        'participations': [{
            'participation_id': p.participation_id,
            'event_id': p.event_id,
            'event_title': p.event.title if p.event else None,
            'event_date': p.event.event_date.isoformat() if p.event and p.event.event_date else None,
            'registration_status': p.registration_status,
            'attended': p.attended,
            'feedback_score': p.feedback_score,
            'certificate_issued': p.certificate_issued
        } for p in participations]
    }), 200
