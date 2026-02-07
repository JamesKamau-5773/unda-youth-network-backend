import json
from datetime import datetime, timezone
from models import db, ResourceItem


def _parse_tags(val):
    if not val:
        return None
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            # allow comma-separated fallback
            return [t.strip() for t in val.split(',') if t.strip()]
    return val


def create_resource_item(data: dict, creator_id: int) -> ResourceItem:
    title = (data.get('title') or '').strip()
    url = data.get('url')
    description = data.get('description')
    resource_type = data.get('resource_type')
    tags = _parse_tags(data.get('tags'))

    if not title:
        raise ValueError('Title is required')

    published = data.get('published', True)
    if isinstance(published, str):
        published = published.lower() in ('true', '1', 'on', 'yes')

    item = ResourceItem(
        title=title,
        url=url,
        description=description,
        resource_type=resource_type,
        tags=tags,
        published=bool(published),
        published_at=datetime.now(timezone.utc) if published else None,
        created_by=creator_id
    )
    db.session.add(item)
    db.session.commit()
    return item


def update_resource_item(resource_id: int, data: dict) -> ResourceItem:
    item = db.session.get(ResourceItem, resource_id)
    if not item:
        raise ValueError('Resource item not found')
    item.title = data.get('title', item.title)
    item.url = data.get('url', item.url)
    item.description = data.get('description', item.description)
    item.resource_type = data.get('resource_type', item.resource_type)
    if 'tags' in data:
        item.tags = _parse_tags(data.get('tags'))

    if 'published' in data:
        was_published = item.published
        published = data['published']
        if isinstance(published, str):
            published = published.lower() in ('true', '1', 'on', 'yes')
        item.published = bool(published)
        if not was_published and item.published:
            item.published_at = datetime.now(timezone.utc)
        elif not item.published:
            item.published_at = None

    item.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return item


def delete_resource_item(resource_id: int) -> None:
    item = db.session.get(ResourceItem, resource_id)
    if not item:
        raise ValueError('Resource item not found')
    db.session.delete(item)
    db.session.commit()


def toggle_publish_resource(resource_id: int) -> ResourceItem:
    item = db.session.get(ResourceItem, resource_id)
    if not item:
        raise ValueError('Resource item not found')
    was_published = item.published
    item.published = not was_published
    if not was_published and item.published:
        item.published_at = datetime.now(timezone.utc)
    item.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return item


def list_resource_items():
    return db.session.query(ResourceItem).order_by(ResourceItem.created_at.desc()).all()
