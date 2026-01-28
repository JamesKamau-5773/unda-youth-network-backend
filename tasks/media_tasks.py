"""Thumbnail generation task with an optional Celery worker.

If Celery is installed the task will be a real Celery task. Otherwise a
synchronous function with the same name is provided so the rest of the app
can call it directly during development without Celery.
"""
from flask import current_app

# Do not create a Celery instance here. The worker process should create and
# bind a Celery instance (see `celery_worker.py`) so tasks are registered on
# the same Celery app the worker runs. We keep a synchronous fallback for
# development when Celery isn't available.
celery = None


def _generate_and_store_thumbnail(gallery_id, media_path):
    try:
        from models import db, MediaGallery
        from services.file_utils import generate_thumbnail

        thumb = generate_thumbnail(media_path)
        if not thumb:
            return ''

        gallery = db.session.get(MediaGallery, gallery_id)
        if not gallery:
            return ''

        changed = False
        items = gallery.media_items or []
        for item in items:
            if isinstance(item, dict) and item.get('path') == media_path:
                item['thumbnail'] = thumb
                changed = True

        if changed:
            gallery.media_items = items
            db.session.add(gallery)
            db.session.commit()

        return thumb
    except Exception:
        try:
            current_app.logger.exception('Thumbnail generation task failed for %s', media_path)
        except Exception:
            pass
        raise


if celery:
    @celery.task(name='tasks.generate_and_store_thumbnail')
    def generate_and_store_thumbnail(gallery_id, media_path):
        return _generate_and_store_thumbnail(gallery_id, media_path)
else:
    # Provide synchronous fallback so the app works without Celery installed
    def generate_and_store_thumbnail(gallery_id, media_path):
        return _generate_and_store_thumbnail(gallery_id, media_path)

