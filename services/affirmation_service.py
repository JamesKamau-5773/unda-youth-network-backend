from typing import Optional
from models import db, DailyAffirmation
from datetime import datetime, timezone


def _parse_date(val):
    if not val:
        return None
    if isinstance(val, str):
        try:
            return datetime.strptime(val, '%Y-%m-%d').date()
        except Exception:
            raise ValueError('scheduled_date must be YYYY-MM-DD')
    return val


def create_affirmation(data: dict, creator_id: int) -> DailyAffirmation:
    content = (data.get('content') or '').strip()
    theme = data.get('theme')
    scheduled_date = _parse_date(data.get('scheduled_date'))

    if not content:
        raise ValueError('Content is required')

    affirmation = DailyAffirmation(
        content=content,
        theme=theme,
        scheduled_date=scheduled_date,
        created_by=creator_id
    )
    db.session.add(affirmation)
    db.session.commit()
    return affirmation


def update_affirmation(affirmation_id: int, data: dict) -> DailyAffirmation:
    affirmation = db.session.get(DailyAffirmation, affirmation_id)
    if not affirmation:
        raise ValueError('Affirmation not found')
    affirmation.content = data.get('content', affirmation.content)
    affirmation.theme = data.get('theme', affirmation.theme)
    affirmation.scheduled_date = _parse_date(data.get('scheduled_date')) or affirmation.scheduled_date
    affirmation.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return affirmation


def delete_affirmation(affirmation_id: int) -> None:
    affirmation = db.session.get(DailyAffirmation, affirmation_id)
    if not affirmation:
        raise ValueError('Affirmation not found')
    db.session.delete(affirmation)
    db.session.commit()


def list_affirmations():
    # ordering by scheduled_date desc for admin listing
    return db.session.query(DailyAffirmation).order_by(DailyAffirmation.scheduled_date.desc()).all()
