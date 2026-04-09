import os
from datetime import datetime, timezone
from flask import current_app
from werkzeug.utils import secure_filename
from PIL import Image

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'docx', 'pptx', 'mp4', 'mov', 'webm', 'mkv', 'ogg', 'avi'}

# Grouped by category for display
ALLOWED_EXTENSIONS_BY_TYPE = {
    'Images': ['png', 'jpg', 'jpeg', 'gif'],
    'Videos': ['mp4', 'mov', 'webm', 'mkv', 'avi', 'ogg'],
    'Documents': ['pdf', 'docx', 'pptx']
}

def get_allowed_extensions_display():
    """Return human-readable list of allowed file extensions."""
    return ', '.join(sorted(ALLOWED_EXTENSIONS))

def get_allowed_extensions_formatted():
    """Return formatted list of allowed extensions by category."""
    formatted = []
    for category, exts in ALLOWED_EXTENSIONS_BY_TYPE.items():
        formatted.append(f"{category}: {', '.join(exts)}")
    return ' | '.join(formatted)


def _allowed(filename: str) -> bool:
    if not filename:
        return False
    ext = filename.rsplit('.', 1)[-1].lower()
    return ext in ALLOWED_EXTENSIONS


def _get_file_extension(fileobj) -> str:
    """Extract file extension from FileStorage object.
    
    Tries: original filename -> MIME type -> None
    Returns extension WITH the leading dot (e.g., '.jpeg'), or empty string if not found.
    """
    # Try from original filename
    if hasattr(fileobj, 'filename') and fileobj.filename:
        if '.' in fileobj.filename:
            ext = fileobj.filename.rsplit('.', 1)[-1].lower()
            return f'.{ext}' if ext else ''
    
    # Try from MIME type
    if hasattr(fileobj, 'mimetype') and fileobj.mimetype:
        mime_type = fileobj.mimetype.lower()
        # Map common MIME types to extensions
        mime_to_ext = {
            'image/jpeg': '.jpeg',
            'image/jpg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'audio/mpeg': '.mp3',
            'audio/wav': '.wav',
            'audio/ogg': '.ogg',
            'audio/mp4': '.m4a',
            'video/mp4': '.mp4',
            'video/quicktime': '.mov',
            'video/x-matroska': '.mkv',
            'video/webm': '.webm',
            'application/pdf': '.pdf',
            'application/msword': '.docx',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        }
        return mime_to_ext.get(mime_type, '')
    
    return ''


def save_file(fileobj, subdir='uploads') -> str:
    """Validate and save a FileStorage object. 
    Returns:
      - Cloudinary public URL if USE_CLOUDINARY is enabled
      - S3 HTTPS URL if USE_S3 is enabled
      - Relative local path if using local filesystem
    """
    if not hasattr(fileobj, 'filename') or not hasattr(fileobj, 'save'):
        raise ValueError('Invalid file object')

    filename = secure_filename(fileobj.filename)
    if not _allowed(filename):
        allowed = get_allowed_extensions_display()
        raise ValueError(f'File type not allowed. Accepted formats: {allowed}')
    
    # Ensure filename has proper extension; if secure_filename stripped it or it's missing, recover it
    if '.' not in filename:
        extension = _get_file_extension(fileobj)
        if extension:
            filename = filename + extension
        else:
            allowed = get_allowed_extensions_display()
            raise ValueError(f'Cannot determine file type. Accepted formats: {allowed}')

    # If Cloudinary is enabled, upload to Cloudinary
    if current_app.config.get('USE_CLOUDINARY'):
        try:
            import cloudinary.uploader
            import cloudinary
            
            # Read file content
            fileobj.stream.seek(0)
            data = fileobj.read()
            fileobj.stream.seek(0)
            
            # Prepare upload options
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')
            public_id = f"{subdir}/{timestamp}_{filename.rsplit('.', 1)[0]}"
            
            # Get file extension to determine resource type
            ext = filename.rsplit('.', 1)[-1].lower()
            resource_type = 'auto'  # 'auto' detects if it's image, video, raw, etc.
            
            # Determine if video based on extension
            video_extensions = {'mp4', 'mov', 'webm', 'mkv', 'avi', 'ogg', 'm4v', 'flv', 'wmv', 'asf', 'rm', 'rmvb'}
            if ext in video_extensions:
                resource_type = 'video'
            
            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(
                data,
                resource_type=resource_type,
                public_id=public_id,
                use_filename=True,
                unique_filename=False,
                folder=subdir,
                overwrite=True
            )
            
            # Return the secure HTTPS URL
            url = upload_result.get('secure_url')
            if not url:
                url = upload_result.get('url', '')
            
            current_app.logger.info('File uploaded to Cloudinary: %s -> %s', filename, url)
            return url
            
        except Exception as e:
            current_app.logger.exception('Cloudinary upload failed: %s', str(e))
            raise ValueError(f'Failed to upload to Cloudinary: {str(e)}')

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
    """Create a thumbnail for an image path or cloud URL (Cloudinary/S3).
    
    Returns:
      - Cloudinary thumbnail transformation URL (for Cloudinary uploads)
      - S3 thumbnail URL (for S3 uploads)  
      - Local thumbnail path (for local files)
    """
    try:
        # If path is an HTTP URL and Cloudinary is enabled, use Cloudinary transformations
        if rel_path.startswith('http') and current_app.config.get('USE_CLOUDINARY'):
            try:
                from cloudinary import CloudinaryResource
                import cloudinary.api
                
                # Extract public_id from Cloudinary URL
                # Cloudinary URLs are like: https://res.cloudinary.com/cloud_name/image/upload/...version/public_id
                # We need to parse the public_id for transformations
                
                # For Cloudinary, we can use the transformation API directly
                # Simply return a transformation URL that crops to 300x300
                # Format: https://res.cloudinary.com/{cloud_name}/image/upload/c_fill,g_auto,h_300,w_300/v1/{public_id}
                
                # Use cloudinary's built-in URL transformation
                from cloudinary.utils import cloudinary_url
                thumb_url, _ = cloudinary_url(
                    rel_path,
                    crop='fill',
                    gravity='auto',
                    height=size[1],
                    width=size[0],
                    quality='auto'
                )
                return thumb_url
                
            except Exception as e:
                current_app.logger.warning('Could not generate Cloudinary thumbnail for %s: %s', rel_path, str(e))
                # Return original URL if transformation fails
                return rel_path
        
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
