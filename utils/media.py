"""Shared helpers for normalising media-gallery items coming from the DB."""

VIDEO_EXTS = ('.mp4', '.mov', '.webm', '.mkv', '.ogg', '.avi')
PHOTO_EXTS = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')


def infer_type_from_path(path_or_url, fallback='photo', item_type=None):
    """Return 'video', 'photo', or 'youtube' based on file extension or stored type.
    
    Args:
        path_or_url: File path or URL string
        fallback: Default type if cannot be determined
        item_type: Explicit type from item dict (e.g., 'youtube')
    
    Returns:
        Type string: 'video', 'photo', 'youtube', or fallback
    """
    # If item explicitly specifies type as 'youtube', preserve it
    if item_type == 'youtube':
        return 'youtube'
    
    if not path_or_url:
        return fallback
    lower = path_or_url.lower()
    
    # Check for YouTube URLs
    if 'youtube.com/embed' in lower or 'youtu.be' in lower or 'youtube.com/watch' in lower:
        return 'youtube'
    
    # Check for video extensions
    if any(lower.endswith(ext) for ext in VIDEO_EXTS):
        return 'video'
    
    # Check for photo extensions
    if any(lower.endswith(ext) for ext in PHOTO_EXTS):
        return 'photo'
    
    return fallback


def normalize_media_src(item):
    """Resolve the web-accessible URL for a media-item dict.

    Admin uploads store items as ``{'type': 'file', 'path': 'uploads/...'}``.
    Other sources may use ``url``, ``src``, or ``file_url`` keys.  This helper
    checks all of them and converts local filesystem paths to public API URLs
    at ``/api/media/...`` to ensure public access without authentication.
    """
    if not isinstance(item, dict):
        return None
    src = item.get('url') or item.get('src') or item.get('file_url')
    if not src:
        path = item.get('path')
        if path:
            if str(path).startswith('http'):
                # Already an absolute URL
                src = path
            else:
                # Convert local filesystem path to public media API endpoint
                # Remove prefixes: instance/, static/, uploads/ - in order
                path_str = str(path)
                normalized = path_str.lstrip('instance/').lstrip('static/').lstrip('uploads/').lstrip('/')
                src = f"/api/media/{normalized}"
    return src


def normalize_gallery_items(raw_items):
    """Return a new list with every item's ``src`` properly resolved.

    Each dict in the returned list keeps its original keys **plus** a
    guaranteed ``src`` and ``type`` field. YouTube items are preserved
    with their type as 'youtube'.
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
        # Preserve explicit type (e.g., 'youtube') or infer from path
        item_type = item.get('type', 'photo')
        normalised['type'] = infer_type_from_path(
            item.get('filename') or src,
            fallback=item_type,
            item_type=item_type
        )
        # Ensure thumbnail falls back to src
        if not normalised.get('thumbnail'):
            normalised['thumbnail'] = src
        out.append(normalised)
    return out
