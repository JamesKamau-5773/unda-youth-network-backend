from datetime import datetime, timezone
from typing import List
from models import db, Podcast


def _parse_tags(val) -> List[str]:
    if not val:
        return []
    if isinstance(val, str):
        return [t.strip() for t in val.split(',') if t.strip()]
    if isinstance(val, (list, tuple)):
        return [str(t).strip() for t in val if str(t).strip()]
    return []


def create_podcast(data: dict, creator_id: int) -> Podcast:
    title = (data.get('title') or '').strip()
    if not title:
        raise ValueError('Title is required')

    tags = _parse_tags(data.get('tags'))

    podcast = Podcast(
        title=title,
        description=data.get('description'),
        guest=data.get('guest'),
        audio_url=data.get('audio_url'),
        thumbnail_url=data.get('thumbnail_url'),
        duration=int(data.get('duration')) if data.get('duration') else None,
        episode_number=int(data.get('episode_number')) if data.get('episode_number') else None,
        season_number=int(data.get('season_number')) if data.get('season_number') else None,
        category=data.get('category') or None,
        tags=tags,
        published=bool(data.get('published')),
        created_by=creator_id,
        created_at=datetime.now(timezone.utc)
    )

    if podcast.published:
        podcast.published_at = datetime.now(timezone.utc)

    db.session.add(podcast)
    db.session.commit()
    return podcast


def update_podcast(podcast_id: int, data: dict) -> Podcast:
    p = db.session.get(Podcast, podcast_id)
    if not p:
        raise ValueError('Podcast not found')
    p.title = data.get('title', p.title)
    p.description = data.get('description', p.description)
    p.guest = data.get('guest', p.guest)
    p.audio_url = data.get('audio_url', p.audio_url)
    p.thumbnail_url = data.get('thumbnail_url', p.thumbnail_url)
    if 'duration' in data:
        p.duration = int(data.get('duration')) if data.get('duration') else None
    if 'episode_number' in data:
        p.episode_number = int(data.get('episode_number')) if data.get('episode_number') else None
    if 'season_number' in data:
        p.season_number = int(data.get('season_number')) if data.get('season_number') else None
    if 'category' in data:
        p.category = data.get('category') or None
    if 'tags' in data:
        p.tags = _parse_tags(data.get('tags'))

    was_published = p.published
    if 'published' in data:
        p.published = bool(data.get('published'))
        if not was_published and p.published:
            p.published_at = datetime.now(timezone.utc)

    p.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return p


def delete_podcast(podcast_id: int) -> None:
    p = db.session.get(Podcast, podcast_id)
    if not p:
        raise ValueError('Podcast not found')
    db.session.delete(p)
    db.session.commit()


def toggle_publish_podcast(podcast_id: int) -> Podcast:
    p = db.session.get(Podcast, podcast_id)
    if not p:
        raise ValueError('Podcast not found')
    was_published = p.published
    p.published = not was_published
    if not was_published and p.published:
        p.published_at = datetime.now(timezone.utc)
    p.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return p


def list_podcasts(published_only: bool = False):
    q = db.session.query(Podcast)
    if published_only:
        q = q.filter_by(published=True).order_by(Podcast.published_at.desc())
    else:
        q = q.order_by(Podcast.created_at.desc())
    return q.all()
