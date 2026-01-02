from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, Event
from decorators import admin_required
from datetime import datetime

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
        'events': [{
            'event_id': e.event_id,
            'title': e.title,
            'description': e.description,
            'event_date': e.event_date.isoformat() if e.event_date else None,
            'location': e.location,
            'event_type': e.event_type,
            'organizer': e.organizer,
            'max_participants': e.max_participants,
            'registration_deadline': e.registration_deadline.isoformat() if e.registration_deadline else None,
            'status': e.status,
            'image_url': e.image_url,
            'created_at': e.created_at.isoformat() if e.created_at else None
        } for e in events]
    }), 200


@events_bp.route('/<int:event_id>', methods=['GET'])
def get_event(event_id):
    """Get a single event by ID."""
    event = Event.query.get_or_404(event_id)
    
    return jsonify({
        'success': True,
        'event': {
            'event_id': event.event_id,
            'title': event.title,
            'description': event.description,
            'event_date': event.event_date.isoformat() if event.event_date else None,
            'location': event.location,
            'event_type': event.event_type,
            'organizer': event.organizer,
            'max_participants': event.max_participants,
            'registration_deadline': event.registration_deadline.isoformat() if event.registration_deadline else None,
            'status': event.status,
            'image_url': event.image_url,
            'created_at': event.created_at.isoformat() if event.created_at else None,
            'updated_at': event.updated_at.isoformat() if event.updated_at else None
        }
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
    event = Event.query.get_or_404(event_id)
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
    
    event.updated_at = datetime.utcnow()
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
    event = Event.query.get_or_404(event_id)
    
    db.session.delete(event)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Event deleted successfully'
    }), 200
