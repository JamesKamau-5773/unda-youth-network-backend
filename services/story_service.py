from datetime import datetime, timezone
import re
from models import db, BlogPost
from sqlalchemy.exc import IntegrityError
from services.file_utils import save_file


def _slugify(value: str) -> str:
    value = (value or '').strip().lower()
    value = re.sub(r'[^a-z0-9]+', '-', value)
    value = re.sub(r'(^-|-$)+', '', value)
    return value


def _unique_slug(slug_base: str) -> str:
    slug = slug_base
    idx = 1
    while BlogPost.query.filter_by(slug=slug).first():
        idx += 1
        slug = f"{slug_base}-{idx}"
    return slug


def create_story(data: dict, author_id: int, publish: bool = False) -> BlogPost:
    title = (data.get('title') or '').strip()
    content = data.get('content')
    excerpt = data.get('excerpt')
    featured_image = data.get('featured_image')

    # support FileStorage for uploads
    if featured_image is not None and hasattr(featured_image, 'filename'):
        featured_image = save_file(featured_image, subdir='stories')

    if not title or not content:
        raise ValueError('Title and content are required')

    slug_base = _slugify(title)
    slug = _unique_slug(slug_base) if slug_base else None

    post = BlogPost(
        title=title,
        slug=slug,
        content=content,
        excerpt=excerpt,
        featured_image=featured_image,
        category='Success Stories',
        author_id=author_id,
        published=bool(publish),
        published_at=datetime.now(timezone.utc) if publish else None
    )
    try:
        db.session.add(post)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise
    return post


def update_story(post_id: int, data: dict) -> BlogPost:
    post = db.session.get(BlogPost, post_id)
    if not post:
        raise ValueError('Post not found')
    post.title = data.get('title', post.title)
    post.content = data.get('content', post.content)
    post.excerpt = data.get('excerpt', post.excerpt)
    post.featured_image = data.get('featured_image', post.featured_image)

    if 'published' in data:
        was_published = post.published
        published = data['published']
        if isinstance(published, str):
            published = published.lower() in ('true', '1', 'on', 'yes')
        post.published = bool(published)
        if not was_published and post.published:
            post.published_at = datetime.now(timezone.utc)
        elif not post.published:
            post.published_at = None

    post.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return post


def delete_story(post_id: int) -> None:
    post = db.session.get(BlogPost, post_id)
    if not post:
        raise ValueError('Post not found')
    db.session.delete(post)
    db.session.commit()


def toggle_publish_story(post_id: int) -> BlogPost:
    post = db.session.get(BlogPost, post_id)
    if not post:
        raise ValueError('Post not found')
    was_published = post.published
    post.published = not was_published
    if not was_published and post.published:
        post.published_at = datetime.now(timezone.utc)
    post.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return post


def list_stories(category: str = 'Success Stories'):
    return db.session.query(BlogPost).filter_by(category=category).order_by(BlogPost.created_at.desc()).all()
