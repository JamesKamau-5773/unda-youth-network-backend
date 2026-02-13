from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from models import db, Event, EventInterest
from decorators import admin_required
from datetime import datetime, timezone
from services.event_submission_service import EventSubmissionService
import re

ALLOWED_EVENT_TYPES = {
    'debate': 'debate',              # Debaters Circle
    'debaters circle': 'debate',
    'debaters_circle': 'debate',
    'mtaani': 'mtaani',              # UMV Mtaani Barazas
    'umv mtaani barazas': 'mtaani',
    'podcast': 'podcast'             # Podcast episodes
}


def _normalize_event_type(value, default=None):
    if not value:
        return default
    normalized = ALLOWED_EVENT_TYPES.get(value.lower())
    return normalized

events_bp = Blueprint('events', __name__, url_prefix='/api/events')


@events_bp.route('/', methods=['GET'])
def list_events():
    """Get all events with optional filtering."""
    status = request.args.get('status')  # Upcoming, Ongoing, Completed, Cancelled
    event_type = request.args.get('type')
    limit = request.args.get('limit', type=int)
    
    query = Event.query
    
    # Exclude pending member submissions from public listings
    # Only show approved submissions or admin-created events
    query = query.filter(
        (Event.submission_status.is_(None)) |  # Admin-created events (no submission_status)
        (Event.submission_status == 'Approved')  # Approved submissions
    )

    if status:
        query = query.filter_by(status=status)
    if event_type:
        normalized = _normalize_event_type(event_type)
        if not normalized:
            return jsonify({'success': False, 'message': 'Invalid event type'}), 400
        query = query.filter_by(event_type=normalized)
    
    # Order by event date
    query = query.order_by(Event.event_date.desc())
    
    if limit:
        query = query.limit(limit)
    
    events = query.all()
    
    return jsonify({
        'success': True,
        'total': len(events),
        'events': [e.to_dict() for e in events]
    }), 200


@events_bp.route('/<int:event_id>', methods=['GET'])
def get_event(event_id):
    """Get a single event by ID."""
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({'success': False, 'message': 'Event not found'}), 404
    
    # Exclude pending member submissions from public view
    if event.submission_status == 'Pending Approval':
        return jsonify({'success': False, 'message': 'Event not found'}), 404
    
    return jsonify({
        'success': True,
        'event': event.to_dict()
    }), 200


@events_bp.route('/', methods=['POST'])
@login_required
@admin_required
def create_event():
    """Create a new event (Admin only)."""
    data = request.get_json()
    
    if not data or not data.get('title') or not data.get('event_date'):
        return jsonify({
            'success': False,
            'message': 'Title and event_date are required'
        }), 400
    
    try:
        event_date = datetime.fromisoformat(data['event_date'].replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return jsonify({
            'success': False,
            'message': 'Invalid event_date format. Use ISO 8601 format.'
        }), 400

    event_type = _normalize_event_type(data.get('event_type'), default='debate')
    if not event_type:
        return jsonify({
            'success': False,
            'message': 'Invalid event_type. Allowed: debate, mtaani, podcast'
        }), 400
    
    registration_deadline = None
    if data.get('registration_deadline'):
        try:
            registration_deadline = datetime.fromisoformat(data['registration_deadline'].replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            pass
    
    event = Event(
        title=data['title'],
        description=data.get('description'),
        event_date=event_date,
        location=data.get('location'),
        event_type=event_type,
        organizer=data.get('organizer'),
        max_participants=data.get('max_participants'),
        registration_deadline=registration_deadline,
        status=data.get('status', 'Upcoming'),
        image_url=data.get('image_url'),
        created_by=current_user.user_id
    )
    
    db.session.add(event)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Event created successfully',
        'event_id': event.event_id
    }), 201


@events_bp.route('/<int:event_id>', methods=['PUT'])
@login_required
@admin_required
def update_event(event_id):
    """Update an existing event (Admin only)."""
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({'success': False, 'message': 'Event not found'}), 404
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'message': 'No data provided'
        }), 400
    
    # Update fields if provided
    if 'title' in data:
        event.title = data['title']
    if 'description' in data:
        event.description = data['description']
    if 'event_date' in data:
        try:
            event.event_date = datetime.fromisoformat(data['event_date'].replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return jsonify({
                'success': False,
                'message': 'Invalid event_date format'
            }), 400
    if 'location' in data:
        event.location = data['location']
    if 'event_type' in data:
        normalized = _normalize_event_type(data['event_type'])
        if not normalized:
            return jsonify({
                'success': False,
                'message': 'Invalid event_type. Allowed: debate, mtaani, podcast'
            }), 400
        event.event_type = normalized
    if 'organizer' in data:
        event.organizer = data['organizer']
    if 'max_participants' in data:
        event.max_participants = data['max_participants']
    if 'registration_deadline' in data:
        try:
            event.registration_deadline = datetime.fromisoformat(data['registration_deadline'].replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            event.registration_deadline = None
    if 'status' in data:
        event.status = data['status']
    if 'image_url' in data:
        event.image_url = data['image_url']
    
    event.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Event updated successfully'
    }), 200


@events_bp.route('/<int:event_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_event(event_id):
    """Delete an event (Admin only)."""
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({'success': False, 'message': 'Event not found'}), 404
    
    db.session.delete(event)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Event deleted successfully'
    }), 200


@events_bp.route('/<int:event_id>/register-interest', methods=['POST'])
def register_event_interest(event_id):
    """Register interest in attending an event (public endpoint)."""
    try:
        # Validate event exists
        event = db.session.get(Event, event_id)
        if not event:
            return jsonify({'success': False, 'error': 'Event not found'}), 404
        
        data = request.get_json(silent=True) or {}
        
        # Normalize field names (accept both camelCase and snake_case)
        full_name = data.get('full_name') or data.get('fullName', '').strip()
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        organization = data.get('organization', '').strip()
        
        # Validate required fields
        if not full_name or not email:
            missing = []
            if not full_name:
                missing.append('full_name')
            if not email:
                missing.append('email')
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing)}'
            }), 400
        
        # Validate email format
        email_re = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        email = email.lower()
        if not email_re.match(email):
            return jsonify({'success': False, 'error': 'Invalid email address'}), 400
        
        # Create interest registration
        interest = EventInterest(
            event_id=event_id,
            full_name=full_name,
            email=email,
            phone=phone or None,
            organization=organization or None,
            user_id=current_user.user_id if current_user.is_authenticated else None
        )
        
        db.session.add(interest)
        db.session.commit()
        
        current_app.logger.info(f'Event interest registered: {interest.full_name} for event {event_id}')
        
        return jsonify({
            'success': True,
            'message': f'Interest registered successfully for {event.title}. Check your email for confirmation.',
            'interest': interest.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Error registering event interest')
        return jsonify({
            'success': False,
            'error': 'An error occurred while registering interest. Please try again.'
        }), 500


@events_bp.route('/submit', methods=['POST'])
@login_required
def submit_event():
    """
    Allow authenticated members to submit a new baraza/mtaani event for admin approval.
    
    Expected JSON:
    {
        "title": "Event title",
        "description": "Event description",
        "event_date": "2026-02-20T14:00:00",
        "location": "Event location",
        "event_type": "mtaani" or "baraza"
    }
    """
    try:
        current_app.logger.info(f'Event submission request from user {current_user.user_id}')
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'description', 'event_date', 'location', 'event_type']
        missing_fields = [f for f in required_fields if not data.get(f)]
        
        if missing_fields:
            error_msg = f'Missing required fields: {", ".join(missing_fields)}'
            current_app.logger.warning(f'Event submission validation failed: {error_msg}')
            return jsonify({
                'success': False,
                'message': error_msg
            }), 400
        
        # Normalize event type
        event_type = data.get('event_type', '').lower()
        if event_type not in ['mtaani', 'baraza']:
            error_msg = 'Event type must be "mtaani" or "baraza"'
            current_app.logger.warning(f'Event submission validation failed: {error_msg}')
            return jsonify({
                'success': False,
                'message': error_msg
            }), 400
        
        # Parse event date
        try:
            event_date = datetime.fromisoformat(data['event_date'].replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            error_msg = 'Invalid event_date format. Use ISO format (2026-02-20T14:00:00)'
            current_app.logger.warning(f'Event submission validation failed: {error_msg}')
            return jsonify({
                'success': False,
                'message': error_msg
            }), 400
        
        # Create submission
        submission_data = {
            'title': data['title'].strip(),
            'description': data['description'].strip(),
            'event_date': event_date,
            'location': data['location'].strip(),
            'event_type': 'mtaani'  # Normalize baraza to mtaani
        }
        
        current_app.logger.debug(f'Creating event submission: {submission_data["title"]}')
        result = EventSubmissionService.create_submission(submission_data, current_user.user_id)
        
        if result.get('success'):
            current_app.logger.info(f'Event submitted successfully for approval by user {current_user.user_id}: {submission_data["title"]} (event_id={result.get("event_id")})')
            return jsonify(result), 201
        else:
            error_msg = result.get('message', 'Unknown error')
            current_app.logger.error(f'Event submission failed for user {current_user.user_id}: {error_msg}')
            return jsonify(result), 400
            
    except Exception as e:
        import traceback
        error_msg = str(e)
        current_app.logger.error(f'Exception while submitting event for user {current_user.user_id}: {error_msg}')
        current_app.logger.error(f'Traceback: {traceback.format_exc()}')
        current_app.logger.exception('Error submitting event')
        return jsonify({
            'success': False,
            'error': 'An error occurred while submitting the event. Please try again.'
        }), 500

