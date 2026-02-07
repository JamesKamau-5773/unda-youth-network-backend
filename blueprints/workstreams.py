"""
Workstreams API Blueprint
Provides public GET endpoints and admin CRUD endpoints for:
- Programs/Workstreams (new model)
- Impact Pillars (new model)
- Resources (uses existing ResourceItem model)
- Stories (uses existing BlogPost model)
- Gallery (uses existing MediaGallery model)
- Toolkits (uses existing InstitutionalToolkitItem model)
- Podcasts (uses existing Podcast model)
- Events (uses existing Event model)

This ensures CRUD from admin dashboard reflects in frontend API.
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from models import (
    db, Program, Pillar, BlogPost, MediaGallery, ResourceItem,
    InstitutionalToolkitItem, Event, Podcast
)
from decorators import admin_required
from datetime import datetime, timezone
import re


workstreams_bp = Blueprint('workstreams', __name__)


def _slugify(text):
    """Convert text to URL-friendly slug."""
    if not text:
        return ''
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text


def _camel_to_snake(name: str) -> str:
    """Convert camelCase to snake_case."""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def normalize_input(payload: dict) -> dict:
    """Normalize incoming JSON payload keys to snake_case and trim string values."""
    if not payload or not isinstance(payload, dict):
        return {}
    out = {}
    for k, v in payload.items():
        nk = _camel_to_snake(k) if any(c.isupper() for c in k) else k
        if isinstance(v, str):
            out[nk] = v.strip()
        else:
            out[nk] = v
    return out


# ============================================================================
# PUBLIC ENDPOINTS - Programs (uses Program model)
# ============================================================================

@workstreams_bp.route('/api/workstreams/programs', methods=['GET'])
def get_programs():
    """List all published programs/workstreams."""
    try:
        programs = Program.query.filter_by(published=True).order_by(Program.order, Program.title).all()
        return jsonify({
            'success': True,
            'programs': [p.to_dict() for p in programs],
            'count': len(programs)
        }), 200
    except Exception as e:
        current_app.logger.exception(f'Error fetching programs: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/workstreams/programs/featured', methods=['GET'])
def get_featured_programs():
    """Get featured programs for homepage."""
    try:
        programs = Program.query.filter_by(published=True, featured=True).order_by(Program.order).all()
        return jsonify({
            'success': True,
            'programs': [p.to_dict() for p in programs],
            'count': len(programs)
        }), 200
    except Exception as e:
        current_app.logger.exception(f'Error fetching featured programs: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/workstreams/programs/<id_or_slug>', methods=['GET'])
def get_program(id_or_slug):
    """Get single program by ID or slug."""
    try:
        if id_or_slug.isdigit():
            program = Program.query.get(int(id_or_slug))
        else:
            program = Program.query.filter_by(slug=id_or_slug).first()
        
        if not program:
            return jsonify({'success': False, 'error': 'Program not found'}), 404
        
        return jsonify({
            'success': True,
            'program': program.to_dict()
        }), 200
    except Exception as e:
        current_app.logger.exception(f'Error fetching program {id_or_slug}: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# PUBLIC ENDPOINTS - Pillars (uses Pillar model)
# ============================================================================

@workstreams_bp.route('/api/workstreams/pillars', methods=['GET'])
def get_pillars():
    """Get impact pillars (Awareness, Access, Advocacy)."""
    try:
        pillars = Pillar.query.order_by(Pillar.order).all()
        return jsonify({
            'success': True,
            'pillars': [p.to_dict() for p in pillars],
            'count': len(pillars)
        }), 200
    except Exception as e:
        current_app.logger.exception(f'Error fetching pillars: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# PUBLIC ENDPOINTS - Resources (uses existing ResourceItem model)
# ============================================================================

@workstreams_bp.route('/api/workstreams/resources', methods=['GET'])
def get_resources():
    """List resources with optional category filter."""
    try:
        category = request.args.get('category')  # publication, toolkit, guide, etc.
        resource_type = request.args.get('type')
        
        query = ResourceItem.query.filter_by(published=True)
        
        if category:
            # Map frontend category to resource_type
            query = query.filter_by(resource_type=category)
        if resource_type:
            query = query.filter_by(resource_type=resource_type)
        
        resources = query.order_by(ResourceItem.created_at.desc()).all()
        
        # Transform to frontend expected format
        result = []
        for r in resources:
            result.append({
                'id': r.resource_id,
                'title': r.title,
                'description': r.description,
                'category': r.resource_type,  # Map resource_type to category
                'downloadUrl': r.url,
                'thumbnail': None,  # ResourceItem doesn't have thumbnail
                'tags': r.tags or [],
                'published': r.published,
                'createdAt': r.created_at.isoformat() if r.created_at else None
            })
        
        return jsonify({
            'success': True,
            'resources': result,
            'count': len(result)
        }), 200
    except Exception as e:
        current_app.logger.exception(f'Error fetching resources: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/workstreams/resources/<int:resource_id>', methods=['GET'])
def get_resource(resource_id):
    """Get single resource by ID."""
    try:
        resource = ResourceItem.query.get(resource_id)
        if not resource:
            return jsonify({'success': False, 'error': 'Resource not found'}), 404
        
        result = {
            'id': resource.resource_id,
            'title': resource.title,
            'description': resource.description,
            'category': resource.resource_type,
            'downloadUrl': resource.url,
            'tags': resource.tags or [],
            'published': resource.published,
            'createdAt': resource.created_at.isoformat() if resource.created_at else None
        }
        
        return jsonify({
            'success': True,
            'resource': result
        }), 200
    except Exception as e:
        current_app.logger.exception(f'Error fetching resource {resource_id}: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# PUBLIC ENDPOINTS - Stories (uses existing BlogPost model)
# ============================================================================

@workstreams_bp.route('/api/workstreams/stories', methods=['GET'])
def get_stories():
    """List stories with optional filters. Uses BlogPost model."""
    try:
        limit = request.args.get('limit', type=int)
        sort = request.args.get('sort', 'latest')
        featured = request.args.get('featured')
        category = request.args.get('category')
        
        query = BlogPost.query.filter_by(published=True)
        
        if category:
            query = query.filter_by(category=category)
        
        if sort == 'latest':
            query = query.order_by(BlogPost.published_at.desc())
        elif sort == 'oldest':
            query = query.order_by(BlogPost.published_at.asc())
        elif sort == 'popular':
            query = query.order_by(BlogPost.views.desc())
        
        if limit:
            query = query.limit(limit)
        
        posts = query.all()
        
        # Transform to frontend expected format
        result = []
        for p in posts:
            author_name = p.author.username if p.author else 'UNDA Team'
            result.append({
                'id': p.post_id,
                'title': p.title,
                'slug': p.slug,
                'excerpt': p.excerpt,
                'content': p.content,
                'author': author_name,
                'date': p.published_at.strftime('%Y-%m-%d') if p.published_at else None,
                'image': p.featured_image,
                'category': p.category,
                'tags': p.tags or [],
                'featured': False,  # BlogPost doesn't have featured field
                'views': p.views
            })
        
        return jsonify({
            'success': True,
            'stories': result,
            'count': len(result)
        }), 200
    except Exception as e:
        current_app.logger.exception(f'Error fetching stories: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/workstreams/stories/<id_or_slug>', methods=['GET'])
def get_story(id_or_slug):
    """Get single story by ID or slug. Uses BlogPost model."""
    try:
        if id_or_slug.isdigit():
            post = BlogPost.query.get(int(id_or_slug))
        else:
            post = BlogPost.query.filter_by(slug=id_or_slug).first()
        
        if not post:
            return jsonify({'success': False, 'error': 'Story not found'}), 404
        
        # Increment view count
        post.views = (post.views or 0) + 1
        db.session.commit()
        
        author_name = post.author.username if post.author else 'UNDA Team'
        result = {
            'id': post.post_id,
            'title': post.title,
            'slug': post.slug,
            'excerpt': post.excerpt,
            'content': post.content,
            'author': author_name,
            'date': post.published_at.strftime('%Y-%m-%d') if post.published_at else None,
            'image': post.featured_image,
            'category': post.category,
            'tags': post.tags or [],
            'views': post.views
        }
        
        return jsonify({
            'success': True,
            'story': result
        }), 200
    except Exception as e:
        current_app.logger.exception(f'Error fetching story {id_or_slug}: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# PUBLIC ENDPOINTS - Gallery (uses existing MediaGallery model)
# ============================================================================

@workstreams_bp.route('/api/workstreams/gallery', methods=['GET'])
def get_gallery():
    """List gallery items. Uses MediaGallery model."""
    try:
        item_type = request.args.get('type')  # photo, video
        featured = request.args.get('featured')
        
        query = MediaGallery.query.filter_by(published=True)
        
        galleries = query.order_by(MediaGallery.created_at.desc()).all()
        
        # Flatten media_items from galleries into individual items
        result = []
        for g in galleries:
            if g.media_items:
                for idx, item in enumerate(g.media_items):
                    item_data = {
                        'id': f"{g.gallery_id}_{idx}",
                        'galleryId': g.gallery_id,
                        'galleryTitle': g.title,
                        'type': item.get('type', 'photo'),
                        'title': item.get('caption', g.title),
                        'src': item.get('url'),
                        'thumbnail': item.get('thumbnail', item.get('url')),
                        'videoUrl': item.get('video_url') or item.get('videoUrl'),
                        'alt': item.get('alt', g.title),
                        'category': g.description or 'general'
                    }
                    
                    # Filter by type if specified
                    if item_type and item_data['type'] != item_type:
                        continue
                    
                    result.append(item_data)
        
        return jsonify({
            'success': True,
            'items': result,
            'count': len(result)
        }), 200
    except Exception as e:
        current_app.logger.exception(f'Error fetching gallery: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/workstreams/gallery/<int:gallery_id>', methods=['GET'])
def get_gallery_item(gallery_id):
    """Get single gallery by ID. Uses MediaGallery model."""
    try:
        gallery = MediaGallery.query.get(gallery_id)
        if not gallery:
            return jsonify({'success': False, 'error': 'Gallery not found'}), 404
        
        # Return the full gallery with all its items
        result = {
            'id': gallery.gallery_id,
            'title': gallery.title,
            'description': gallery.description,
            'items': gallery.media_items or [],
            'featuredMedia': gallery.featured_media,
            'published': gallery.published
        }
        
        return jsonify({
            'success': True,
            'gallery': result
        }), 200
    except Exception as e:
        current_app.logger.exception(f'Error fetching gallery {gallery_id}: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# PUBLIC ENDPOINTS - Toolkits (uses existing InstitutionalToolkitItem model)
# ============================================================================

@workstreams_bp.route('/api/workstreams/toolkits', methods=['GET'])
def get_toolkits():
    """List institutional toolkit items."""
    try:
        category = request.args.get('category')
        
        query = InstitutionalToolkitItem.query.filter_by(published=True)
        
        if category:
            query = query.filter_by(category=category)
        
        items = query.order_by(InstitutionalToolkitItem.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'toolkits': [t.to_dict() for t in items],
            'count': len(items)
        }), 200
    except Exception as e:
        current_app.logger.exception(f'Error fetching toolkits: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/workstreams/toolkits/<int:item_id>', methods=['GET'])
def get_toolkit(item_id):
    """Get single toolkit item by ID."""
    try:
        item = InstitutionalToolkitItem.query.get(item_id)
        if not item:
            return jsonify({'success': False, 'error': 'Toolkit item not found'}), 404
        
        return jsonify({
            'success': True,
            'toolkit': item.to_dict()
        }), 200
    except Exception as e:
        current_app.logger.exception(f'Error fetching toolkit {item_id}: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# PUBLIC ENDPOINTS - Podcasts (uses existing Podcast model)
# ============================================================================

@workstreams_bp.route('/api/workstreams/podcasts', methods=['GET'])
def get_podcasts():
    """List podcasts."""
    try:
        limit = request.args.get('limit', type=int)
        category = request.args.get('category')
        
        query = Podcast.query.filter_by(published=True)
        
        if category:
            query = query.filter_by(category=category)
        
        query = query.order_by(Podcast.published_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        podcasts = query.all()
        
        return jsonify({
            'success': True,
            'podcasts': [p.to_dict() for p in podcasts],
            'count': len(podcasts)
        }), 200
    except Exception as e:
        current_app.logger.exception(f'Error fetching podcasts: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/workstreams/podcasts/<int:podcast_id>', methods=['GET'])
def get_podcast(podcast_id):
    """Get single podcast by ID."""
    try:
        podcast = Podcast.query.get(podcast_id)
        if not podcast:
            return jsonify({'success': False, 'error': 'Podcast not found'}), 404
        
        return jsonify({
            'success': True,
            'podcast': podcast.to_dict()
        }), 200
    except Exception as e:
        current_app.logger.exception(f'Error fetching podcast {podcast_id}: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# PUBLIC ENDPOINTS - Events (uses existing Event model)
# ============================================================================

# Program to event_type mapping
PROGRAM_EVENT_TYPE_MAP = {
    'umv-annual-conference': ['conference'],
    'annual-conference': ['conference'],
    'conference': ['conference'],
    'umv-debaters': ['debate'],
    'debaters': ['debate'],
    'debate': ['debate'],
    'umv-mtaani': ['baraza', 'barazas'],
    'mtaani': ['baraza', 'barazas'],
    'baraza': ['baraza', 'barazas'],
    'umv-global': ['international', 'partnership', 'international partnership', 'international partnerships'],
    'global': ['international', 'partnership', 'international partnership', 'international partnerships'],
    'international': ['international', 'partnership', 'international partnership', 'international partnerships'],
}


@workstreams_bp.route('/api/workstreams/events', methods=['GET'])
def get_workstream_events():
    """List events with optional status and program filter.
    
    Query params:
        status: Event status filter (default: 'Upcoming')
        type: Direct event_type filter
        program: Program slug to filter events by type mapping:
            - 'umv-annual-conference' or 'conference' → conference events
            - 'umv-debaters' or 'debate' → debate events
            - 'umv-mtaani' or 'baraza' → baraza events
            - 'umv-global' or 'international' → international partnership events
        limit: Maximum number of events to return
    """
    try:
        status = request.args.get('status', 'Upcoming')
        event_type = request.args.get('type')  # Direct event_type filter
        program = request.args.get('program')  # Program-based filter
        limit = request.args.get('limit', type=int)
        
        query = Event.query.filter_by(status=status)
        
        # If program is specified, map to event types
        if program:
            program_key = program.lower().strip()
            allowed_types = PROGRAM_EVENT_TYPE_MAP.get(program_key, [])
            if allowed_types:
                # Filter by any of the allowed event types (case-insensitive)
                from sqlalchemy import func
                query = query.filter(func.lower(Event.event_type).in_([t.lower() for t in allowed_types]))
        elif event_type:
            # Direct event_type filter
            query = query.filter_by(event_type=event_type)
        
        query = query.order_by(Event.event_date.asc())
        
        if limit:
            query = query.limit(limit)
        
        events = query.all()
        
        return jsonify({
            'success': True,
            'events': [e.to_dict() for e in events],
            'count': len(events),
            'filter': {
                'program': program,
                'status': status,
                'event_type': event_type
            }
        }), 200
    except Exception as e:
        current_app.logger.exception(f'Error fetching events: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/workstreams/events/<int:event_id>', methods=['GET'])
def get_workstream_event(event_id):
    """Get single event by ID."""
    try:
        event = Event.query.get(event_id)
        
        if not event:
            return jsonify({'success': False, 'error': 'Event not found'}), 404
        
        return jsonify({
            'success': True,
            'event': event.to_dict()
        }), 200
    except Exception as e:
        current_app.logger.exception(f'Error fetching event {event_id}: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# ADMIN ENDPOINTS - Programs (uses Program model - new)
# ============================================================================

@workstreams_bp.route('/api/admin/workstreams/programs', methods=['GET'])
@admin_required
def admin_list_programs():
    """Admin: List all programs (including unpublished)."""
    try:
        programs = Program.query.order_by(Program.order, Program.title).all()
        return jsonify({
            'success': True,
            'programs': [p.to_dict() for p in programs],
            'count': len(programs)
        }), 200
    except Exception as e:
        current_app.logger.exception(f'Admin error listing programs: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/admin/workstreams/programs', methods=['POST'])
@admin_required
def admin_create_program():
    """Admin: Create a new program."""
    try:
        data = normalize_input(request.get_json() or {})
        
        title = data.get('title')
        if not title:
            return jsonify({'success': False, 'error': 'Title is required'}), 400
        
        slug = data.get('slug') or _slugify(title)
        
        if Program.query.filter_by(slug=slug).first():
            return jsonify({'success': False, 'error': 'A program with this slug already exists'}), 400
        
        program = Program(
            title=title,
            slug=slug,
            tagline=data.get('tagline'),
            description=data.get('description'),
            icon=data.get('icon'),
            color=data.get('color'),
            link=data.get('link'),
            cta=data.get('cta', 'Learn More'),
            highlights=data.get('highlights', []),
            featured=data.get('featured', False),
            order=data.get('order', 0),
            published=data.get('published', True),
            created_by=current_user.user_id
        )
        
        db.session.add(program)
        db.session.commit()
        
        current_app.logger.info(f'Admin {current_user.username} created program: {title}')
        
        return jsonify({
            'success': True,
            'message': 'Program created successfully',
            'program': program.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f'Admin error creating program: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/admin/workstreams/programs/<int:program_id>', methods=['PUT'])
@admin_required
def admin_update_program(program_id):
    """Admin: Update a program."""
    try:
        program = Program.query.get(program_id)
        if not program:
            return jsonify({'success': False, 'error': 'Program not found'}), 404
        
        data = normalize_input(request.get_json() or {})
        
        if 'title' in data:
            program.title = data['title']
        if 'slug' in data:
            existing = Program.query.filter(Program.slug == data['slug'], Program.program_id != program_id).first()
            if existing:
                return jsonify({'success': False, 'error': 'A program with this slug already exists'}), 400
            program.slug = data['slug']
        if 'tagline' in data:
            program.tagline = data['tagline']
        if 'description' in data:
            program.description = data['description']
        if 'icon' in data:
            program.icon = data['icon']
        if 'color' in data:
            program.color = data['color']
        if 'link' in data:
            program.link = data['link']
        if 'cta' in data:
            program.cta = data['cta']
        if 'highlights' in data:
            program.highlights = data['highlights']
        if 'featured' in data:
            program.featured = data['featured']
        if 'order' in data:
            program.order = data['order']
        if 'published' in data:
            program.published = data['published']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Program updated successfully',
            'program': program.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f'Admin error updating program {program_id}: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/admin/workstreams/programs/<int:program_id>', methods=['DELETE'])
@admin_required
def admin_delete_program(program_id):
    """Admin: Delete a program."""
    try:
        program = Program.query.get(program_id)
        if not program:
            return jsonify({'success': False, 'error': 'Program not found'}), 404
        
        title = program.title
        db.session.delete(program)
        db.session.commit()
        
        current_app.logger.info(f'Admin {current_user.username} deleted program: {title}')
        
        return jsonify({
            'success': True,
            'message': 'Program deleted successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f'Admin error deleting program {program_id}: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# ADMIN ENDPOINTS - Pillars (uses Pillar model - new)
# ============================================================================

@workstreams_bp.route('/api/admin/workstreams/pillars', methods=['GET'])
@admin_required
def admin_list_pillars():
    """Admin: List all pillars."""
    try:
        pillars = Pillar.query.order_by(Pillar.order).all()
        return jsonify({
            'success': True,
            'pillars': [p.to_dict() for p in pillars],
            'count': len(pillars)
        }), 200
    except Exception as e:
        current_app.logger.exception(f'Admin error listing pillars: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/admin/workstreams/pillars', methods=['POST'])
@admin_required
def admin_create_pillar():
    """Admin: Create a new pillar."""
    try:
        data = normalize_input(request.get_json() or {})
        
        title = data.get('title')
        if not title:
            return jsonify({'success': False, 'error': 'Title is required'}), 400
        
        slug = data.get('slug') or _slugify(title)
        
        pillar = Pillar(
            title=title,
            slug=slug,
            icon=data.get('icon'),
            color=data.get('color'),
            description=data.get('description'),
            order=data.get('order', 0)
        )
        
        db.session.add(pillar)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Pillar created successfully',
            'pillar': pillar.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f'Admin error creating pillar: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/admin/workstreams/pillars/<int:pillar_id>', methods=['PUT'])
@admin_required
def admin_update_pillar(pillar_id):
    """Admin: Update a pillar."""
    try:
        pillar = Pillar.query.get(pillar_id)
        if not pillar:
            return jsonify({'success': False, 'error': 'Pillar not found'}), 404
        
        data = normalize_input(request.get_json() or {})
        
        if 'title' in data:
            pillar.title = data['title']
        if 'slug' in data:
            pillar.slug = data['slug']
        if 'icon' in data:
            pillar.icon = data['icon']
        if 'color' in data:
            pillar.color = data['color']
        if 'description' in data:
            pillar.description = data['description']
        if 'order' in data:
            pillar.order = data['order']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Pillar updated successfully',
            'pillar': pillar.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f'Admin error updating pillar {pillar_id}: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/admin/workstreams/pillars/<int:pillar_id>', methods=['DELETE'])
@admin_required
def admin_delete_pillar(pillar_id):
    """Admin: Delete a pillar."""
    try:
        pillar = Pillar.query.get(pillar_id)
        if not pillar:
            return jsonify({'success': False, 'error': 'Pillar not found'}), 404
        
        db.session.delete(pillar)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Pillar deleted successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f'Admin error deleting pillar {pillar_id}: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# SEED DATA ENDPOINT (for initial setup)
# ============================================================================

@workstreams_bp.route('/api/admin/workstreams/seed', methods=['POST'])
@admin_required
def seed_workstreams_data():
    """Admin: Seed initial programs and pillars data."""
    try:
        seeded = {'programs': 0, 'pillars': 0}
        
        # Seed Pillars if empty
        if Pillar.query.count() == 0:
            pillars = [
                Pillar(title='Awareness', slug='awareness', icon='Lightbulb', color='yellow',
                       description='Raising awareness about mental health and destigmatizing conversations around it.', order=1),
                Pillar(title='Access', slug='access', icon='Heart', color='red',
                       description='Improving access to mental health resources and support services.', order=2),
                Pillar(title='Advocacy', slug='advocacy', icon='Users', color='blue',
                       description='Advocating for policies and systems that support youth mental health.', order=3)
            ]
            for p in pillars:
                db.session.add(p)
            seeded['pillars'] = len(pillars)
        
        # Seed Programs if empty
        if Program.query.count() == 0:
            programs = [
                Program(
                    title='UMV Debaters',
                    slug='debaters-circle',
                    tagline='Critical Thinking Through Structured Debates',
                    description='A dynamic platform where high school students explore mental health topics through structured debates, developing critical thinking and communication skills.',
                    icon='MessageSquare',
                    color='teal',
                    link='/debaters-circle',
                    cta='Learn More',
                    highlights=['Structured debate format', 'Mental health topics', 'Youth leadership development'],
                    featured=True,
                    order=1
                ),
                Program(
                    title='UMV Globetrotters',
                    slug='globetrotters',
                    tagline='Global Mental Health Ambassadors',
                    description='Youth ambassadors connecting across borders to share mental health awareness and create global impact.',
                    icon='Globe',
                    color='navy',
                    link='/globetrotters',
                    cta='Join Us',
                    highlights=['International connections', 'Cultural exchange', 'Global advocacy'],
                    featured=True,
                    order=2
                ),
                Program(
                    title='UMV Mentorship',
                    slug='mentorship',
                    tagline='Peer Support and Guidance',
                    description='A structured mentorship program pairing experienced advocates with newcomers for peer support.',
                    icon='Users',
                    color='purple',
                    link='/mentorship',
                    cta='Get Involved',
                    highlights=['Peer-to-peer support', 'Structured guidance', 'Community building'],
                    featured=True,
                    order=3
                ),
                Program(
                    title='UMV Campus',
                    slug='campus',
                    tagline='University Mental Health Initiatives',
                    description='Bringing mental health awareness and resources to university and college campuses.',
                    icon='GraduationCap',
                    color='orange',
                    link='/campus',
                    cta='Explore',
                    highlights=['Campus outreach', 'Student wellness', 'University partnerships'],
                    featured=True,
                    order=4
                ),
                Program(
                    title='UMV Podcast',
                    slug='podcast',
                    tagline='Conversations That Matter',
                    description='A podcast series featuring discussions on mental health, featuring experts and youth voices.',
                    icon='Mic2',
                    color='pink',
                    link='/podcast',
                    cta='Listen Now',
                    highlights=['Expert interviews', 'Youth stories', 'Mental health education'],
                    featured=True,
                    order=5
                ),
                Program(
                    title='UMV Events',
                    slug='events',
                    tagline='Community Gatherings and Workshops',
                    description='Regular events including workshops, conferences, and community gatherings focused on mental health.',
                    icon='Calendar',
                    color='green',
                    link='/events',
                    cta='View Events',
                    highlights=['Workshops', 'Conferences', 'Community engagement'],
                    featured=True,
                    order=6
                )
            ]
            for p in programs:
                db.session.add(p)
            seeded['programs'] = len(programs)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Seed data created successfully',
            'seeded': seeded
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f'Error seeding workstreams data: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# AGGREGATED CONTENT ENDPOINT - All workstreams content for homepage
# ============================================================================

@workstreams_bp.route('/api/workstreams/all', methods=['GET'])
def get_all_workstreams():
    """Get aggregated workstreams content for homepage/overview."""
    try:
        # Get counts and recent items from each model
        result = {
            'programs': {
                'count': Program.query.filter_by(published=True).count(),
                'featured': [p.to_dict() for p in Program.query.filter_by(published=True, featured=True).order_by(Program.order).limit(6).all()]
            },
            'pillars': {
                'count': Pillar.query.count(),
                'items': [p.to_dict() for p in Pillar.query.order_by(Pillar.order).all()]
            },
            'stories': {
                'count': BlogPost.query.filter_by(published=True).count(),
                'recent': [{'id': p.post_id, 'title': p.title, 'slug': p.slug, 'excerpt': p.excerpt, 'image': p.featured_image, 'category': p.category} 
                          for p in BlogPost.query.filter_by(published=True).order_by(BlogPost.published_at.desc()).limit(3).all()]
            },
            'resources': {
                'count': ResourceItem.query.filter_by(published=True).count(),
                'recent': [{'id': r.resource_id, 'title': r.title, 'category': r.resource_type}
                          for r in ResourceItem.query.filter_by(published=True).order_by(ResourceItem.created_at.desc()).limit(3).all()]
            },
            'galleries': {
                'count': MediaGallery.query.filter_by(published=True).count(),
                'recent': [{'id': g.gallery_id, 'title': g.title, 'featuredMedia': g.featured_media}
                          for g in MediaGallery.query.filter_by(published=True).order_by(MediaGallery.created_at.desc()).limit(3).all()]
            },
            'podcasts': {
                'count': Podcast.query.filter_by(published=True).count(),
                'recent': [{'id': p.podcast_id, 'title': p.title, 'guest': p.guest, 'thumbnailUrl': p.thumbnail_url}
                          for p in Podcast.query.filter_by(published=True).order_by(Podcast.published_at.desc()).limit(3).all()]
            },
            'events': {
                'upcoming_count': Event.query.filter_by(status='Upcoming').count(),
                'upcoming': [e.to_dict() for e in Event.query.filter_by(status='Upcoming').order_by(Event.event_date.asc()).limit(3).all()]
            },
            'toolkits': {
                'count': InstitutionalToolkitItem.query.filter_by(published=True).count(),
                'recent': [{'id': t.item_id, 'title': t.title, 'category': t.category}
                          for t in InstitutionalToolkitItem.query.filter_by(published=True).order_by(InstitutionalToolkitItem.created_at.desc()).limit(3).all()]
            }
        }
        
        return jsonify({
            'success': True,
            'workstreams': result
        }), 200
    except Exception as e:
        current_app.logger.exception(f'Error fetching all workstreams: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500
