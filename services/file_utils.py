import os
from datetime import datetime, timezone
from flask import current_app
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'docx', 'pptx'}


def _allowed(filename: str) -> bool:
    if not filename:
        return False
    ext = filename.rsplit('.', 1)[-1].lower()
    return ext in ALLOWED_EXTENSIONS


def save_file(fileobj, subdir='uploads') -> str:
    """Validate and save a FileStorage object. Returns relative path."""
    if not hasattr(fileobj, 'filename') or not hasattr(fileobj, 'save'):
        raise ValueError('Invalid file object')

    filename = secure_filename(fileobj.filename)
    if not _allowed(filename):
        raise ValueError('File type not allowed')

    uploads_root = current_app.config.get('UPLOAD_FOLDER') or os.path.join(current_app.instance_path, 'uploads')
    target_dir = os.path.join(uploads_root, subdir)
    os.makedirs(target_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')
    target_name = f"{timestamp}_{filename}"
    target_path = os.path.join(target_dir, target_name)

    fileobj.save(target_path)

    # Return a path relative to the instance or uploads root for DB storage
    rel = os.path.relpath(target_path, current_app.root_path)
    return rel
