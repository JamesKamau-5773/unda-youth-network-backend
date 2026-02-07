import json
from datetime import datetime, timezone
from models import db, MediaGallery
from services.file_utils import save_file
from flask import current_app
from tasks.media_tasks import generate_and_store_thumbnail


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

    # If file objects provided, save them and produce media metadata list.
    # Thumbnail generation is queued to a background task to avoid blocking requests.
    if media_items and isinstance(media_items, (list, tuple)):
        parsed = []
        for m in media_items:
            if hasattr(m, 'filename') and hasattr(m, 'save'):
                path = save_file(m, subdir='media_galleries')
                # do not block: enqueue thumbnail generation and store empty thumbnail for now
                parsed.append({'type': 'file', 'path': path, 'thumbnail': '', 'filename': m.filename})
            else:
                parsed.append(m)
        media_items = parsed
    else:
        media_items = _parse_media_items(media_items)

    if not title:
        raise ValueError('Title is required')

    # Determine published state; default to True when created via admin
    published = data.get('published', True)
    if isinstance(published, str):
        published = published.lower() in ('true', '1', 'on', 'yes')

    gallery = MediaGallery(
        title=title,
        description=description,
        media_items=media_items,
        published=published,
        published_at=datetime.now(timezone.utc) if published else None,
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
    if 'published' in data:
        was_published = gallery.published
        published = data['published']
        if isinstance(published, str):
            published = published.lower() in ('true', '1', 'on', 'yes')
        gallery.published = published
        # Set published_at when first published
        if published and not was_published:
            gallery.published_at = datetime.now(timezone.utc)
        elif not published:
            gallery.published_at = None
    if 'media_items' in data:
        media_items = data.get('media_items')
        if media_items and isinstance(media_items, (list, tuple)):
            parsed = []
            for m in media_items:
                if hasattr(m, 'filename') and hasattr(m, 'save'):
                    path = save_file(m, subdir='media_galleries')
                    parsed.append({'type': 'file', 'path': path, 'thumbnail': '', 'filename': m.filename})
                else:
                    parsed.append(m)
            gallery.media_items = parsed
        else:
            gallery.media_items = _parse_media_items(media_items)
    gallery.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    # Queue thumbnail generation for any newly saved image files
    try:
        items = gallery.media_items or []
        for it in items:
            if isinstance(it, dict) and it.get('type') == 'file' and not it.get('thumbnail'):
                fn = it.get('filename','').lower()
                if any(fn.endswith(ext) for ext in ('.png','.jpg','.jpeg','.gif')):
                    try:
                        generate_and_store_thumbnail.delay(gallery.id, it.get('path'))
                    except Exception:
                        current_app.logger.exception('Failed to enqueue thumbnail task')
    except Exception:
        current_app.logger.exception('Error scheduling thumbnail tasks')

    return gallery


def delete_media_gallery(gallery_id: int) -> None:
    gallery = db.session.get(MediaGallery, gallery_id)
    if not gallery:
        raise ValueError('Media gallery not found')
    db.session.delete(gallery)
    db.session.commit()


def toggle_publish_gallery(gallery_id: int) -> MediaGallery:
    gallery = db.session.get(MediaGallery, gallery_id)
    if not gallery:
        raise ValueError('Media gallery not found')
    was_published = gallery.published
    gallery.published = not was_published
    if not was_published and gallery.published:
        gallery.published_at = datetime.now(timezone.utc)
    gallery.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return gallery


def list_media_galleries(published_only: bool = False):
    q = db.session.query(MediaGallery)
    if published_only:
        q = q.filter_by(published=True).order_by(MediaGallery.published_at.desc())
    else:
        q = q.order_by(MediaGallery.created_at.desc())
    return q.all()
