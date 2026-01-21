from datetime import datetime, timezone
from typing import Optional, Dict, Any
from flask import current_app
from models import db, Event


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M')
    except ValueError:
        raise ValueError('Invalid date format')


def _parse_int(value: Optional[str]) -> Optional[int]:
    if value in (None, ''):
        return None
    try:
        return int(value)
    except Exception:
        raise ValueError('Invalid integer value')


def create_event(data: Dict[str, Any], creator_id: int) -> Event:
    title = (data.get('title') or '').strip()
    motion = (data.get('motion') or '').strip()
    event_date = _parse_datetime(data.get('event_date'))

    if not title or not motion or not event_date:
        raise ValueError('Title, motion, and event date are required')

    registration_deadline = None
    if data.get('registration_deadline'):
        registration_deadline = _parse_datetime(data.get('registration_deadline'))

    max_participants = None
    if 'max_participants' in data:
        max_participants = _parse_int(data.get('max_participants'))

    event = Event(
        title=title,
        description=data.get('description'),
        event_date=event_date,
        location=data.get('location'),
        event_type=data.get('event_type', 'debate'),
        organizer=data.get('organizer'),
        max_participants=max_participants,
        registration_deadline=registration_deadline,
        status=data.get('status', 'Upcoming'),
        image_url=data.get('image_url'),
        motion=motion,
        created_by=creator_id,
    )

    try:
        db.session.add(event)
        db.session.commit()
        return event
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error creating event')
        raise


def update_event(event_id: int, data: Dict[str, Any]) -> Event:
    event = db.session.get(Event, event_id)
    if not event:
        raise ValueError('Event not found')
    title = (data.get('title') or '').strip()
    motion = (data.get('motion') or '').strip()
    event_date = _parse_datetime(data.get('event_date'))

    if not title or not motion or not event_date:
        raise ValueError('Title, motion, and event date are required')

    registration_deadline = None
    if data.get('registration_deadline'):
        registration_deadline = _parse_datetime(data.get('registration_deadline'))

    max_participants = None
    if 'max_participants' in data:
        max_participants = _parse_int(data.get('max_participants'))

    event.title = title
    event.description = data.get('description')
    event.event_date = event_date
    event.location = data.get('location')
    event.organizer = data.get('organizer')
    event.max_participants = max_participants
    event.registration_deadline = registration_deadline
    event.status = data.get('status', 'Upcoming')
    event.image_url = data.get('image_url')
    event.motion = motion
    event.updated_at = datetime.now(timezone.utc)

    try:
        db.session.commit()
        return event
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error updating event')
        raise
