import os
from datetime import datetime, timezone
from flask import current_app
from werkzeug.utils import secure_filename
from PIL import Image

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'docx', 'pptx', 'mp4', 'mov', 'webm', 'mkv', 'ogg', 'avi'}


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

    # If S3 is enabled, upload to S3 and return an HTTPS URL
    if current_app.config.get('USE_S3'):
        # Lazy import boto3 to avoid hard dependency when S3 is not used
        import boto3
        key_prefix = subdir.rstrip('/') + '/'
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')
        key = f"{key_prefix}{timestamp}_{filename}"

        # Read file content
        try:
            fileobj.stream.seek(0)
        except Exception:
            pass
        data = fileobj.read()

        s3 = boto3.client('s3',
                          aws_access_key_id=current_app.config.get('S3_ACCESS_KEY'),
                          aws_secret_access_key=current_app.config.get('S3_SECRET_ACCESS_KEY'),
                          region_name=current_app.config.get('S3_REGION'))
        extra_args = {'ACL': 'public-read'}
        content_type = getattr(fileobj, 'mimetype', None)
        if content_type:
            extra_args['ContentType'] = content_type

        s3.put_object(Bucket=current_app.config.get('S3_BUCKET'), Key=key, Body=data, **extra_args)

        region = current_app.config.get('S3_REGION')
        if region:
            url = f"https://{current_app.config.get('S3_BUCKET')}.s3.{region}.amazonaws.com/{key}"
        else:
            url = f"https://{current_app.config.get('S3_BUCKET')}.s3.amazonaws.com/{key}"
        return url

    # Fallback to local filesystem
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


def generate_thumbnail(rel_path: str, size=(300, 300)) -> str:
    """Create a thumbnail for an image path or S3 URL.
    Returns an HTTPS URL (for S3) or a path relative to app.root_path for local files.
    """
    try:
        # If path is an HTTP URL (S3), download object and create thumbnail in-memory then upload
        if rel_path.startswith('http') and current_app.config.get('USE_S3'):
            import boto3
            import io
            from urllib.parse import urlparse
            # parse bucket and key from URL
            parsed = urlparse(rel_path)
            path = parsed.path.lstrip('/')
            bucket = current_app.config.get('S3_BUCKET')
            region = current_app.config.get('S3_REGION')

            s3 = boto3.client('s3',
                              aws_access_key_id=current_app.config.get('S3_ACCESS_KEY'),
                              aws_secret_access_key=current_app.config.get('S3_SECRET_ACCESS_KEY'),
                              region_name=region)

            # download into memory
            obj = s3.get_object(Bucket=bucket, Key=path)
            body = obj['Body'].read()
            img = Image.open(io.BytesIO(body))
            img.thumbnail(size)

            # save thumbnail into memory and upload back to S3 under thumbnails/
            thumb_buf = io.BytesIO()
            img.save(thumb_buf, format=img.format or 'PNG')
            thumb_buf.seek(0)

            thumb_key = os.path.join(os.path.dirname(path), 'thumbnails', f"thumb_{os.path.basename(path)}")
            s3.put_object(Bucket=bucket, Key=thumb_key, Body=thumb_buf.read(), ACL='public-read', ContentType=obj.get('ContentType','image/jpeg'))

            if region:
                thumb_url = f"https://{bucket}.s3.{region}.amazonaws.com/{thumb_key}"
            else:
                thumb_url = f"https://{bucket}.s3.amazonaws.com/{thumb_key}"
            return thumb_url

        # Local file path handling
        abs_path = os.path.join(current_app.root_path, rel_path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(abs_path)

        img = Image.open(abs_path)
        img.thumbnail(size)

        base_dir = os.path.dirname(abs_path)
        thumbs_dir = os.path.join(base_dir, 'thumbnails')
        os.makedirs(thumbs_dir, exist_ok=True)

        base_name = os.path.basename(abs_path)
        thumb_name = f"thumb_{base_name}"
        thumb_path = os.path.join(thumbs_dir, thumb_name)
        img.save(thumb_path)

        rel_thumb = os.path.relpath(thumb_path, current_app.root_path)
        return rel_thumb
    except Exception:
        current_app.logger.exception('Failed to create thumbnail for %s', rel_path)
        return ''
