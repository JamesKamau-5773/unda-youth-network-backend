"""Shared helpers for normalising media-gallery items coming from the DB."""

VIDEO_EXTS = ('.mp4', '.mov', '.webm', '.mkv', '.ogg', '.avi')
PHOTO_EXTS = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')


def infer_type_from_path(path_or_url, fallback='photo'):
    """Return 'video' or 'photo' based on file extension."""
    if not path_or_url:
        return fallback
    lower = path_or_url.lower()
    if any(lower.endswith(ext) for ext in VIDEO_EXTS):
        return 'video'
    if any(lower.endswith(ext) for ext in PHOTO_EXTS):
        return 'photo'
    return fallback


def normalize_media_src(item):
    """Resolve the web-accessible URL for a media-item dict.

    Admin uploads store items as ``{'type': 'file', 'path': 'static/uploads/...'}``.
    Other sources may use ``url``, ``src``, or ``file_url`` keys.  This helper
    checks all of them and converts local ``static/…`` paths to ``/static/…``
    URLs suitable for the public frontend.
    """
    if not isinstance(item, dict):
        return None
    src = item.get('url') or item.get('src') or item.get('file_url')
    if not src:
        path = item.get('path')
        if path:
            if path.startswith('http'):
                src = path
            elif path.startswith('static/'):
                src = f"/{path}"
            else:
                src = f"/static/{path.lstrip('/')}"
    return src


def normalize_gallery_items(raw_items):
    """Return a new list with every item's ``src`` properly resolved.

    Each dict in the returned list keeps its original keys **plus** a
    guaranteed ``src`` and ``type`` field.
    """
    if not raw_items:
        return []
    out = []
    for item in raw_items:
        src = normalize_media_src(item)
        if not src:
            continue
        normalised = dict(item)
        normalised['src'] = src
        normalised['type'] = infer_type_from_path(
            item.get('filename') or src,
            fallback=item.get('type', 'photo'),
        )
        # Ensure thumbnail falls back to src
        if not normalised.get('thumbnail'):
            normalised['thumbnail'] = src
        out.append(normalised)
    return out
