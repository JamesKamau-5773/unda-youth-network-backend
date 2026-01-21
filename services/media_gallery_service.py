import json
from datetime import datetime, timezone
from models import db, MediaGallery
from services.file_utils import save_file


def _parse_media_items(val):
    if not val:
        return None
    # If file objects are provided (FileStorage list), save elsewhere; controllers pass saved paths or JSON
    # If it's a string, try JSON
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            raise ValueError('media_items must be valid JSON')
    # If it's a list-like (already parsed), return as-is
    return val


def create_media_gallery(data: dict, creator_id: int) -> MediaGallery:
    title = (data.get('title') or '').strip()
    description = data.get('description')
    media_items = data.get('media_items')

    # If file objects provided, save them and produce media metadata list
    if media_items and isinstance(media_items, (list, tuple)):
        parsed = []
        for m in media_items:
            if hasattr(m, 'filename') and hasattr(m, 'save'):
                path = save_file(m, subdir='media_galleries')
                parsed.append({'type': 'file', 'path': path, 'filename': m.filename})
            else:
                parsed.append(m)
        media_items = parsed
    else:
        media_items = _parse_media_items(media_items)

    if not title:
        raise ValueError('Title is required')

    gallery = MediaGallery(
        title=title,
        description=description,
        media_items=media_items,
        created_by=creator_id
    )
    db.session.add(gallery)
    db.session.commit()
    return gallery


def update_media_gallery(gallery_id: int, data: dict) -> MediaGallery:
    gallery = db.session.get(MediaGallery, gallery_id)
    if not gallery:
        raise ValueError('Media gallery not found')
    gallery.title = data.get('title', gallery.title)
    gallery.description = data.get('description', gallery.description)
    if 'media_items' in data:
        media_items = data.get('media_items')
        if media_items and isinstance(media_items, (list, tuple)):
            parsed = []
            for m in media_items:
                if hasattr(m, 'filename') and hasattr(m, 'save'):
                    path = save_file(m, subdir='media_galleries')
                    parsed.append({'type': 'file', 'path': path, 'filename': m.filename})
                else:
                    parsed.append(m)
            gallery.media_items = parsed
        else:
            gallery.media_items = _parse_media_items(media_items)
    gallery.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return gallery


def delete_media_gallery(gallery_id: int) -> None:
    gallery = db.session.get(MediaGallery, gallery_id)
    if not gallery:
        raise ValueError('Media gallery not found')
    db.session.delete(gallery)
    db.session.commit()


def list_media_galleries(published_only: bool = False):
    q = db.session.query(MediaGallery)
    if published_only:
        q = q.filter_by(published=True).order_by(MediaGallery.published_at.desc())
    else:
        q = q.order_by(MediaGallery.created_at.desc())
    return q.all()
