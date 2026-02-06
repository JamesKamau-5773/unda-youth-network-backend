"""
Workstreams API Blueprint
Provides public GET endpoints and admin CRUD endpoints for:
- Programs/Workstreams
- Impact Pillars
- Resources
- Stories
- Gallery Items
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from models import db, Program, Pillar, Story, GalleryItem, WorkstreamResource
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
# PUBLIC ENDPOINTS - Programs
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
        current_app.logger.error(f'Error fetching programs: {str(e)}')
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
        current_app.logger.error(f'Error fetching featured programs: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/workstreams/programs/<id_or_slug>', methods=['GET'])
def get_program(id_or_slug):
    """Get single program by ID or slug."""
    try:
        # Try by ID first
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
        current_app.logger.error(f'Error fetching program {id_or_slug}: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# PUBLIC ENDPOINTS - Pillars
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
        current_app.logger.error(f'Error fetching pillars: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# PUBLIC ENDPOINTS - Resources
# ============================================================================

@workstreams_bp.route('/api/workstreams/resources', methods=['GET'])
def get_resources():
    """List resources with optional category filter."""
    try:
        category = request.args.get('category')
        featured = request.args.get('featured')
        
        query = WorkstreamResource.query.filter_by(published=True)
        
        if category:
            query = query.filter_by(category=category)
        if featured and featured.lower() == 'true':
            query = query.filter_by(featured=True)
        
        resources = query.order_by(WorkstreamResource.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'resources': [r.to_dict() for r in resources],
            'count': len(resources)
        }), 200
    except Exception as e:
        current_app.logger.error(f'Error fetching resources: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/workstreams/resources/<int:resource_id>', methods=['GET'])
def get_resource(resource_id):
    """Get single resource by ID."""
    try:
        resource = WorkstreamResource.query.get(resource_id)
        if not resource:
            return jsonify({'success': False, 'error': 'Resource not found'}), 404
        
        return jsonify({
            'success': True,
            'resource': resource.to_dict()
        }), 200
    except Exception as e:
        current_app.logger.error(f'Error fetching resource {resource_id}: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# PUBLIC ENDPOINTS - Stories
# ============================================================================

@workstreams_bp.route('/api/workstreams/stories', methods=['GET'])
def get_stories():
    """List stories with optional filters."""
    try:
        limit = request.args.get('limit', type=int)
        sort = request.args.get('sort', 'latest')
        featured = request.args.get('featured')
        category = request.args.get('category')
        
        query = Story.query.filter_by(published=True)
        
        if featured and featured.lower() == 'true':
            query = query.filter_by(featured=True)
        if category:
            query = query.filter_by(category=category)
        
        if sort == 'latest':
            query = query.order_by(Story.date.desc())
        elif sort == 'oldest':
            query = query.order_by(Story.date.asc())
        elif sort == 'popular':
            query = query.order_by(Story.views.desc())
        
        if limit:
            query = query.limit(limit)
        
        stories = query.all()
        
        return jsonify({
            'success': True,
            'stories': [s.to_dict() for s in stories],
            'count': len(stories)
        }), 200
    except Exception as e:
        current_app.logger.error(f'Error fetching stories: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/workstreams/stories/<id_or_slug>', methods=['GET'])
def get_story(id_or_slug):
    """Get single story by ID or slug."""
    try:
        if id_or_slug.isdigit():
            story = Story.query.get(int(id_or_slug))
        else:
            story = Story.query.filter_by(slug=id_or_slug).first()
        
        if not story:
            return jsonify({'success': False, 'error': 'Story not found'}), 404
        
        # Increment view count
        story.views = (story.views or 0) + 1
        db.session.commit()
        
        return jsonify({
            'success': True,
            'story': story.to_dict()
        }), 200
    except Exception as e:
        current_app.logger.error(f'Error fetching story {id_or_slug}: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# PUBLIC ENDPOINTS - Gallery
# ============================================================================

@workstreams_bp.route('/api/workstreams/gallery', methods=['GET'])
def get_gallery():
    """List gallery items with optional filters."""
    try:
        item_type = request.args.get('type')
        featured = request.args.get('featured')
        category = request.args.get('category')
        
        query = GalleryItem.query.filter_by(published=True)
        
        if item_type:
            query = query.filter_by(type=item_type)
        if featured and featured.lower() == 'true':
            query = query.filter_by(featured=True)
        if category:
            query = query.filter_by(category=category)
        
        items = query.order_by(GalleryItem.order, GalleryItem.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'items': [i.to_dict() for i in items],
            'count': len(items)
        }), 200
    except Exception as e:
        current_app.logger.error(f'Error fetching gallery: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/workstreams/gallery/<int:item_id>', methods=['GET'])
def get_gallery_item(item_id):
    """Get single gallery item by ID."""
    try:
        item = GalleryItem.query.get(item_id)
        if not item:
            return jsonify({'success': False, 'error': 'Gallery item not found'}), 404
        
        return jsonify({
            'success': True,
            'item': item.to_dict()
        }), 200
    except Exception as e:
        current_app.logger.error(f'Error fetching gallery item {item_id}: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# PUBLIC ENDPOINTS - Events (using existing Event model)
# ============================================================================

@workstreams_bp.route('/api/workstreams/events', methods=['GET'])
def get_workstream_events():
    """List events with optional status filter."""
    try:
        from models import Event
        
        status = request.args.get('status', 'Upcoming')
        limit = request.args.get('limit', type=int)
        
        query = Event.query.filter_by(status=status).order_by(Event.event_date.asc())
        
        if limit:
            query = query.limit(limit)
        
        events = query.all()
        
        return jsonify({
            'success': True,
            'events': [e.to_dict() for e in events],
            'count': len(events)
        }), 200
    except Exception as e:
        current_app.logger.error(f'Error fetching events: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/workstreams/events/<id_or_slug>', methods=['GET'])
def get_workstream_event(id_or_slug):
    """Get single event by ID."""
    try:
        from models import Event
        
        if id_or_slug.isdigit():
            event = Event.query.get(int(id_or_slug))
        else:
            event = Event.query.filter_by(title=id_or_slug).first()
        
        if not event:
            return jsonify({'success': False, 'error': 'Event not found'}), 404
        
        return jsonify({
            'success': True,
            'event': event.to_dict()
        }), 200
    except Exception as e:
        current_app.logger.error(f'Error fetching event {id_or_slug}: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# ADMIN ENDPOINTS - Programs
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
        current_app.logger.error(f'Admin error listing programs: {str(e)}')
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
        
        # Check for duplicate slug
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
        current_app.logger.error(f'Admin error creating program: {str(e)}')
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
        
        # Update fields if provided
        if 'title' in data:
            program.title = data['title']
        if 'slug' in data:
            # Check for duplicate slug
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
        
        current_app.logger.info(f'Admin {current_user.username} updated program: {program.title}')
        
        return jsonify({
            'success': True,
            'message': 'Program updated successfully',
            'program': program.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin error updating program {program_id}: {str(e)}')
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
        current_app.logger.error(f'Admin error deleting program {program_id}: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# ADMIN ENDPOINTS - Pillars
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
        current_app.logger.error(f'Admin error listing pillars: {str(e)}')
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
        current_app.logger.error(f'Admin error creating pillar: {str(e)}')
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
        current_app.logger.error(f'Admin error updating pillar {pillar_id}: {str(e)}')
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
        current_app.logger.error(f'Admin error deleting pillar {pillar_id}: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# ADMIN ENDPOINTS - Resources
# ============================================================================

@workstreams_bp.route('/api/admin/workstreams/resources', methods=['GET'])
@admin_required
def admin_list_resources():
    """Admin: List all resources."""
    try:
        resources = WorkstreamResource.query.order_by(WorkstreamResource.created_at.desc()).all()
        return jsonify({
            'success': True,
            'resources': [r.to_dict() for r in resources],
            'count': len(resources)
        }), 200
    except Exception as e:
        current_app.logger.error(f'Admin error listing resources: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/admin/workstreams/resources', methods=['POST'])
@admin_required
def admin_create_resource():
    """Admin: Create a new resource."""
    try:
        data = normalize_input(request.get_json() or {})
        
        title = data.get('title')
        if not title:
            return jsonify({'success': False, 'error': 'Title is required'}), 400
        
        resource = WorkstreamResource(
            title=title,
            description=data.get('description'),
            category=data.get('category'),
            download_url=data.get('download_url'),
            thumbnail=data.get('thumbnail'),
            tags=data.get('tags', []),
            file_type=data.get('file_type'),
            file_size=data.get('file_size'),
            published=data.get('published', True),
            featured=data.get('featured', False),
            created_by=current_user.user_id
        )
        
        db.session.add(resource)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Resource created successfully',
            'resource': resource.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin error creating resource: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/admin/workstreams/resources/<int:resource_id>', methods=['PUT'])
@admin_required
def admin_update_resource(resource_id):
    """Admin: Update a resource."""
    try:
        resource = WorkstreamResource.query.get(resource_id)
        if not resource:
            return jsonify({'success': False, 'error': 'Resource not found'}), 404
        
        data = normalize_input(request.get_json() or {})
        
        if 'title' in data:
            resource.title = data['title']
        if 'description' in data:
            resource.description = data['description']
        if 'category' in data:
            resource.category = data['category']
        if 'download_url' in data:
            resource.download_url = data['download_url']
        if 'thumbnail' in data:
            resource.thumbnail = data['thumbnail']
        if 'tags' in data:
            resource.tags = data['tags']
        if 'file_type' in data:
            resource.file_type = data['file_type']
        if 'file_size' in data:
            resource.file_size = data['file_size']
        if 'published' in data:
            resource.published = data['published']
        if 'featured' in data:
            resource.featured = data['featured']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Resource updated successfully',
            'resource': resource.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin error updating resource {resource_id}: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/admin/workstreams/resources/<int:resource_id>', methods=['DELETE'])
@admin_required
def admin_delete_resource(resource_id):
    """Admin: Delete a resource."""
    try:
        resource = WorkstreamResource.query.get(resource_id)
        if not resource:
            return jsonify({'success': False, 'error': 'Resource not found'}), 404
        
        db.session.delete(resource)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Resource deleted successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin error deleting resource {resource_id}: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# ADMIN ENDPOINTS - Stories
# ============================================================================

@workstreams_bp.route('/api/admin/workstreams/stories', methods=['GET'])
@admin_required
def admin_list_stories():
    """Admin: List all stories."""
    try:
        stories = Story.query.order_by(Story.created_at.desc()).all()
        return jsonify({
            'success': True,
            'stories': [s.to_dict() for s in stories],
            'count': len(stories)
        }), 200
    except Exception as e:
        current_app.logger.error(f'Admin error listing stories: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/admin/workstreams/stories', methods=['POST'])
@admin_required
def admin_create_story():
    """Admin: Create a new story."""
    try:
        data = normalize_input(request.get_json() or {})
        
        title = data.get('title')
        if not title:
            return jsonify({'success': False, 'error': 'Title is required'}), 400
        
        slug = data.get('slug') or _slugify(title)
        
        # Check for duplicate slug
        if Story.query.filter_by(slug=slug).first():
            return jsonify({'success': False, 'error': 'A story with this slug already exists'}), 400
        
        story = Story(
            title=title,
            slug=slug,
            excerpt=data.get('excerpt'),
            content=data.get('content'),
            author=data.get('author'),
            author_id=current_user.user_id,
            date=datetime.now(timezone.utc),
            image=data.get('image'),
            category=data.get('category'),
            tags=data.get('tags', []),
            featured=data.get('featured', False),
            published=data.get('published', False)
        )
        
        if data.get('published'):
            story.published_at = datetime.now(timezone.utc)
        
        db.session.add(story)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Story created successfully',
            'story': story.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin error creating story: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/admin/workstreams/stories/<int:story_id>', methods=['PUT'])
@admin_required
def admin_update_story(story_id):
    """Admin: Update a story."""
    try:
        story = Story.query.get(story_id)
        if not story:
            return jsonify({'success': False, 'error': 'Story not found'}), 404
        
        data = normalize_input(request.get_json() or {})
        
        if 'title' in data:
            story.title = data['title']
        if 'slug' in data:
            existing = Story.query.filter(Story.slug == data['slug'], Story.story_id != story_id).first()
            if existing:
                return jsonify({'success': False, 'error': 'A story with this slug already exists'}), 400
            story.slug = data['slug']
        if 'excerpt' in data:
            story.excerpt = data['excerpt']
        if 'content' in data:
            story.content = data['content']
        if 'author' in data:
            story.author = data['author']
        if 'image' in data:
            story.image = data['image']
        if 'category' in data:
            story.category = data['category']
        if 'tags' in data:
            story.tags = data['tags']
        if 'featured' in data:
            story.featured = data['featured']
        if 'published' in data:
            story.published = data['published']
            if data['published'] and not story.published_at:
                story.published_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Story updated successfully',
            'story': story.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin error updating story {story_id}: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/admin/workstreams/stories/<int:story_id>', methods=['DELETE'])
@admin_required
def admin_delete_story(story_id):
    """Admin: Delete a story."""
    try:
        story = Story.query.get(story_id)
        if not story:
            return jsonify({'success': False, 'error': 'Story not found'}), 404
        
        db.session.delete(story)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Story deleted successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin error deleting story {story_id}: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# ADMIN ENDPOINTS - Gallery
# ============================================================================

@workstreams_bp.route('/api/admin/workstreams/gallery', methods=['GET'])
@admin_required
def admin_list_gallery():
    """Admin: List all gallery items."""
    try:
        items = GalleryItem.query.order_by(GalleryItem.order, GalleryItem.created_at.desc()).all()
        return jsonify({
            'success': True,
            'items': [i.to_dict() for i in items],
            'count': len(items)
        }), 200
    except Exception as e:
        current_app.logger.error(f'Admin error listing gallery: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/admin/workstreams/gallery', methods=['POST'])
@admin_required
def admin_create_gallery_item():
    """Admin: Create a new gallery item."""
    try:
        data = normalize_input(request.get_json() or {})
        
        title = data.get('title')
        item_type = data.get('type')
        
        if not title:
            return jsonify({'success': False, 'error': 'Title is required'}), 400
        if not item_type or item_type not in ('photo', 'video'):
            return jsonify({'success': False, 'error': 'Type must be "photo" or "video"'}), 400
        
        item = GalleryItem(
            type=item_type,
            title=title,
            src=data.get('src'),
            thumbnail=data.get('thumbnail'),
            video_url=data.get('video_url'),
            alt=data.get('alt'),
            category=data.get('category'),
            featured=data.get('featured', False),
            published=data.get('published', True),
            order=data.get('order', 0),
            created_by=current_user.user_id
        )
        
        db.session.add(item)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Gallery item created successfully',
            'item': item.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin error creating gallery item: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/admin/workstreams/gallery/<int:item_id>', methods=['PUT'])
@admin_required
def admin_update_gallery_item(item_id):
    """Admin: Update a gallery item."""
    try:
        item = GalleryItem.query.get(item_id)
        if not item:
            return jsonify({'success': False, 'error': 'Gallery item not found'}), 404
        
        data = normalize_input(request.get_json() or {})
        
        if 'type' in data:
            item.type = data['type']
        if 'title' in data:
            item.title = data['title']
        if 'src' in data:
            item.src = data['src']
        if 'thumbnail' in data:
            item.thumbnail = data['thumbnail']
        if 'video_url' in data:
            item.video_url = data['video_url']
        if 'alt' in data:
            item.alt = data['alt']
        if 'category' in data:
            item.category = data['category']
        if 'featured' in data:
            item.featured = data['featured']
        if 'published' in data:
            item.published = data['published']
        if 'order' in data:
            item.order = data['order']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Gallery item updated successfully',
            'item': item.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin error updating gallery item {item_id}: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@workstreams_bp.route('/api/admin/workstreams/gallery/<int:item_id>', methods=['DELETE'])
@admin_required
def admin_delete_gallery_item(item_id):
    """Admin: Delete a gallery item."""
    try:
        item = GalleryItem.query.get(item_id)
        if not item:
            return jsonify({'success': False, 'error': 'Gallery item not found'}), 404
        
        db.session.delete(item)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Gallery item deleted successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Admin error deleting gallery item {item_id}: {str(e)}')
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
        current_app.logger.error(f'Error seeding workstreams data: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500
