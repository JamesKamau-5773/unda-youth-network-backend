import json
from datetime import datetime, timezone
from models import db, InstitutionalToolkitItem
from services.file_utils import save_file


def _parse_attachments(val):
    if not val:
        return None
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            raise ValueError('attachments must be valid JSON')
    # allow lists of already-saved attachment metadata
    return val


def create_toolkit_item(data: dict, creator_id: int) -> InstitutionalToolkitItem:
    title = (data.get('title') or '').strip()
    content = data.get('content')
    attachments = data.get('attachments')

    if attachments and isinstance(attachments, (list, tuple)):
        parsed = []
        for a in attachments:
            if hasattr(a, 'filename') and hasattr(a, 'save'):
                path = save_file(a, subdir='toolkit')
                parsed.append({'type': 'file', 'path': path, 'filename': a.filename})
            else:
                parsed.append(a)
        attachments = parsed
    else:
        attachments = _parse_attachments(attachments)
    if not title:
        raise ValueError('Title is required')

    published = data.get('published', True)
    if isinstance(published, str):
        published = published.lower() in ('true', '1', 'on', 'yes')

    item = InstitutionalToolkitItem(
        title=title,
        content=content,
        attachments=attachments,
        published=bool(published),
        created_by=creator_id
    )
    db.session.add(item)
    db.session.commit()
    return item


def update_toolkit_item(item_id: int, data: dict) -> InstitutionalToolkitItem:
    item = db.session.get(InstitutionalToolkitItem, item_id)
    if not item:
        raise ValueError('Toolkit item not found')
    item.title = data.get('title', item.title)
    item.content = data.get('content', item.content)
    if 'attachments' in data:
        attachments = data.get('attachments')
        if attachments and isinstance(attachments, (list, tuple)):
            parsed = []
            for a in attachments:
                if hasattr(a, 'filename') and hasattr(a, 'save'):
                    path = save_file(a, subdir='toolkit')
                    parsed.append({'type': 'file', 'path': path, 'filename': a.filename})
                else:
                    parsed.append(a)
            item.attachments = parsed
        else:
            item.attachments = _parse_attachments(attachments)
    if 'published' in data:
        published = data['published']
        if isinstance(published, str):
            published = published.lower() in ('true', '1', 'on', 'yes')
        item.published = bool(published)

    item.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return item


def delete_toolkit_item(item_id: int) -> None:
    item = db.session.get(InstitutionalToolkitItem, item_id)
    if not item:
        raise ValueError('Toolkit item not found')
    db.session.delete(item)
    db.session.commit()


def toggle_publish_toolkit(item_id: int) -> InstitutionalToolkitItem:
    item = db.session.get(InstitutionalToolkitItem, item_id)
    if not item:
        raise ValueError('Toolkit item not found')
    item.published = not item.published
    item.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return item


def list_toolkit_items(published_only: bool = False):
    q = db.session.query(InstitutionalToolkitItem)
    if published_only:
        q = q.filter_by(published=True)
    q = q.order_by(InstitutionalToolkitItem.created_at.desc())
    return q.all()
