from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, BlogPost
from decorators import admin_required, supervisor_required
from datetime import datetime
import re

blog_bp = Blueprint('blog', __name__, url_prefix='/api/blog')


def generate_slug(title):
    """Generate URL-friendly slug from title."""
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = slug.strip('-')
    return slug


@blog_bp.route('/', methods=['GET'])
def list_posts():
    """Get all blog posts with optional filtering."""
    category = request.args.get('category')
    published_only = request.args.get('published', 'true').lower() == 'true'
    limit = request.args.get('limit', type=int)
    
    query = BlogPost.query
    
    if published_only:
        query = query.filter_by(published=True)
    if category:
        query = query.filter_by(category=category)
    
    # Order by published date or created date
    query = query.order_by(BlogPost.published_at.desc().nullslast(), BlogPost.created_at.desc())
    
    if limit:
        query = query.limit(limit)
    
    posts = query.all()
    
    return jsonify({
        'success': True,
        'total': len(posts),
        'posts': [{
            **p.to_dict(),
            'author': {
                'user_id': p.author.user_id,
                'username': p.author.username
            } if p.author else None
        } for p in posts]
    }), 200


@blog_bp.route('/<int:post_id>', methods=['GET'])
def get_post_by_id(post_id):
    """Get a single blog post by ID."""
    post = BlogPost.query.get_or_404(post_id)
    
    # Increment view count
    post.views += 1
    db.session.commit()
    
    return jsonify({
        'success': True,
        'post': {
            'post_id': post.post_id,
            'title': post.title,
            'slug': post.slug,
            'content': post.content,
            'excerpt': post.excerpt,
            'category': post.category,
            'tags': post.tags,
            'featured_image': post.featured_image,
            'published': post.published,
            'published_at': post.published_at.isoformat() if post.published_at else None,
            'created_at': post.created_at.isoformat() if post.created_at else None,
            'updated_at': post.updated_at.isoformat() if post.updated_at else None,
            'views': post.views,
            'author': {
                'user_id': post.author.user_id,
                'username': post.author.username
            } if post.author else None
        }
    }), 200


@blog_bp.route('/slug/<slug>', methods=['GET'])
def get_post_by_slug(slug):
    """Get a single blog post by slug."""
    post = BlogPost.query.filter_by(slug=slug).first_or_404()
    
    # Increment view count
    post.views += 1
    db.session.commit()
    
    return jsonify({
        'success': True,
        'post': {
            'post_id': post.post_id,
            'title': post.title,
            'slug': post.slug,
            'content': post.content,
            'excerpt': post.excerpt,
            'category': post.category,
            'tags': post.tags,
            'featured_image': post.featured_image,
            'published': post.published,
            'published_at': post.published_at.isoformat() if post.published_at else None,
            'created_at': post.created_at.isoformat() if post.created_at else None,
            'updated_at': post.updated_at.isoformat() if post.updated_at else None,
            'views': post.views,
            'author': {
                'user_id': post.author.user_id,
                'username': post.author.username
            } if post.author else None
        }
    }), 200


@blog_bp.route('/', methods=['POST'])
@login_required
@supervisor_required  # Admins and Supervisors can create blog posts
def create_post():
    """Create a new blog post."""
    data = request.get_json()
    
    if not data or not data.get('title') or not data.get('content'):
        return jsonify({
            'success': False,
            'message': 'Title and content are required'
        }), 400
    
    # Generate slug from title
    slug = generate_slug(data['title'])
    
    # Ensure slug is unique
    existing_post = BlogPost.query.filter_by(slug=slug).first()
    if existing_post:
        # Append timestamp to make unique
        slug = f"{slug}-{int(datetime.utcnow().timestamp())}"
    
    post = BlogPost(
        title=data['title'],
        slug=slug,
        content=data['content'],
        excerpt=data.get('excerpt'),
        author_id=current_user.user_id,
        category=data.get('category'),
        tags=data.get('tags', []),
        featured_image=data.get('featured_image'),
        published=data.get('published', False)
    )
    
    if post.published:
        post.published_at = datetime.utcnow()
    
    db.session.add(post)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Blog post created successfully',
        'post_id': post.post_id,
        'slug': post.slug
    }), 201


@blog_bp.route('/<int:post_id>', methods=['PUT'])
@login_required
@supervisor_required
def update_post(post_id):
    """Update an existing blog post."""
    post = BlogPost.query.get_or_404(post_id)
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'message': 'No data provided'
        }), 400
    
    # Update fields if provided
    if 'title' in data:
        post.title = data['title']
        # Regenerate slug if title changed
        new_slug = generate_slug(data['title'])
        if new_slug != post.slug:
            existing_post = BlogPost.query.filter_by(slug=new_slug).filter(BlogPost.post_id != post_id).first()
            if not existing_post:
                post.slug = new_slug
    
    if 'content' in data:
        post.content = data['content']
    if 'excerpt' in data:
        post.excerpt = data['excerpt']
    if 'category' in data:
        post.category = data['category']
    if 'tags' in data:
        post.tags = data['tags']
    if 'featured_image' in data:
        post.featured_image = data['featured_image']
    
    # Handle publishing
    if 'published' in data:
        was_published = post.published
        post.published = data['published']
        
        # Set published_at when first published
        if post.published and not was_published:
            post.published_at = datetime.utcnow()
        # Clear published_at when unpublished
        elif not post.published and was_published:
            post.published_at = None
    
    post.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Blog post updated successfully'
    }), 200


@blog_bp.route('/<int:post_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_post(post_id):
    """Delete a blog post (Admin only)."""
    post = BlogPost.query.get_or_404(post_id)
    
    db.session.delete(post)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Blog post deleted successfully'
    }), 200
