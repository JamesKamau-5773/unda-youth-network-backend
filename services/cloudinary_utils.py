"""Cloudinary utility functions for managing cloud-hosted media."""

from flask import current_app
import logging

logger = logging.getLogger(__name__)


def delete_cloudinary_file(url: str) -> bool:
    """Delete a file from Cloudinary by its URL.
    
    Args:
        url: Cloudinary URL (e.g., https://res.cloudinary.com/cloud-name/image/upload/...)
        
    Returns:
        True if deleted successfully, False otherwise
    """
    if not url or not url.startswith('https://res.cloudinary.com'):
        logger.warning('Invalid Cloudinary URL: %s', url)
        return False
    
    if not current_app.config.get('USE_CLOUDINARY'):
        logger.debug('Cloudinary not enabled, skipping delete for %s', url)
        return False
    
    try:
        import cloudinary.uploader
        
        # Extract public_id from Cloudinary URL
        # URL format: https://res.cloudinary.com/{cloud_name}/image/upload/v{version}/{public_id}{extension}
        # or: https://res.cloudinary.com/{cloud_name}/video/upload/v{version}/{public_id}{extension}
        
        # Find the public_id by parsing the URL
        # Split by '/upload/' to get the path after upload
        if '/upload/' not in url:
            logger.warning('Could not parse Cloudinary URL: %s', url)
            return False
        
        # Get the part after 'upload/'
        after_upload = url.split('/upload/', 1)[1]
        
        # Remove version info (v{number}/) if present
        if after_upload.startswith('v'):
            parts = after_upload.split('/', 1)
            if len(parts) > 1:
                after_upload = parts[1]
        
        # Remove file extension from the end
        if '.' in after_upload:
            public_id = after_upload.rsplit('.', 1)[0]
        else:
            public_id = after_upload
        
        # Handle nested public_ids with slashes
        # Cloudinary allows folders: media_galleries/timestamp_filename
        logger.debug('Deleting Cloudinary file with public_id: %s', public_id)
        
        # Determine resource type from URL (image vs video)
        resource_type = 'image'
        if '/video/upload/' in url:
            resource_type = 'video'
        elif '/raw/upload/' in url:
            resource_type = 'raw'
        
        result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
        
        if result.get('result') == 'ok':
            logger.info('Successfully deleted Cloudinary file: %s', public_id)
            return True
        else:
            logger.warning('Failed to delete Cloudinary file: %s, result: %s', public_id, result)
            return False
            
    except Exception as e:
        logger.exception('Error deleting Cloudinary file %s: %s', url, str(e))
        return False


def delete_media_files(media_items: list) -> dict:
    """Delete multiple media files. Supports mixed Cloudinary, S3, and local files.
    
    Args:
        media_items: List of dicts with 'url' key (can be Cloudinary, S3, or local path)
        
    Returns:
        Dict with counts: {'deleted': int, 'failed': int, 'skipped': int}
    """
    stats = {'deleted': 0, 'failed': 0, 'skipped': 0}
    
    if not media_items:
        return stats
    
    for item in media_items:
        if not isinstance(item, dict):
            continue
        
        url = item.get('url')
        if not url:
            stats['skipped'] += 1
            continue
        
        # Handle Cloudinary URLs
        if 'res.cloudinary.com' in str(url):
            if delete_cloudinary_file(url):
                stats['deleted'] += 1
            else:
                stats['failed'] += 1
        
        # Handle S3 URLs
        elif 's3' in str(url) and 'amazonaws.com' in str(url):
            if _delete_s3_file(url):
                stats['deleted'] += 1
            else:
                stats['failed'] += 1
        
        # Handle local paths
        elif isinstance(url, str) and not url.startswith('http'):
            if _delete_local_file(url):
                stats['deleted'] += 1
            else:
                stats['failed'] += 1
        
        else:
            stats['skipped'] += 1
    
    return stats


def _delete_s3_file(url: str) -> bool:
    """Delete a file from S3 by its URL."""
    if not current_app.config.get('USE_S3'):
        logger.debug('S3 not enabled, skipping delete for %s', url)
        return False
    
    try:
        import boto3
        from urllib.parse import urlparse
        
        # Parse S3 URL to get bucket and key
        parsed = urlparse(url)
        
        # Extract bucket and key from URL
        # Format: https://{bucket}.s3.{region}.amazonaws.com/{key}
        # or: https://{bucket}.s3.amazonaws.com/{key}
        path_parts = parsed.netloc.split('.')
        bucket = path_parts[0]
        key = parsed.path.lstrip('/')
        
        s3 = boto3.client('s3',
                          aws_access_key_id=current_app.config.get('S3_ACCESS_KEY'),
                          aws_secret_access_key=current_app.config.get('S3_SECRET_KEY'),
                          region_name=current_app.config.get('S3_REGION'))
        
        s3.delete_object(Bucket=bucket, Key=key)
        logger.info('Deleted S3 file: s3://%s/%s', bucket, key)
        return True
        
    except Exception as e:
        logger.exception('Error deleting S3 file %s: %s', url, str(e))
        return False


def _delete_local_file(path: str) -> bool:
    """Delete a local file by its path."""
    try:
        import os
        
        abs_path = os.path.join(current_app.root_path, path)
        if os.path.exists(abs_path):
            os.remove(abs_path)
            logger.info('Deleted local file: %s', abs_path)
            return True
        else:
            logger.warning('Local file not found: %s', abs_path)
            return False
            
    except Exception as e:
        logger.exception('Error deleting local file %s: %s', path, str(e))
        return False
