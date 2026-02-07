from flask import Blueprint, request, jsonify, current_app
from models import db, Podcast
from decorators import admin_required
from flask_login import login_required, current_user
from datetime import datetime, timezone

podcasts_bp = Blueprint('podcasts', __name__, url_prefix='/api/podcasts')


@podcasts_bp.route('', methods=['GET'])
def get_podcasts():
    """
    Get all podcasts with optional filtering.
    Query params:
    - published: true/false (filter by published status)
    - category: filter by category
    - season: filter by season number
    - limit: number of results (default 50)
    - offset: pagination offset (default 0)
    """
    try:
        query = Podcast.query
        
        # Filter by published status
        published = request.args.get('published')
        if published is not None:
            is_published = published.lower() == 'true'
            query = query.filter_by(published=is_published)
        
        # Filter by category
        category = request.args.get('category')
        if category:
            query = query.filter_by(category=category)
        
        # Filter by season
        season = request.args.get('season')
        if season:
            query = query.filter_by(season_number=int(season))
        
        # Pagination
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Order by episode number descending (newest first)
        query = query.order_by(Podcast.created_at.desc())
        
        total = query.count()
        podcasts = query.limit(limit).offset(offset).all()
        
        return jsonify({
            'success': True,
            'podcasts': [p.to_dict() for p in podcasts],
            'total': total,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        current_app.logger.exception('Error fetching podcasts')
        return jsonify({
            'success': False,
            'message': f'Error fetching podcasts: {str(e)}'
        }), 500


@podcasts_bp.route('/<int:podcast_id>', methods=['GET'])
def get_podcast(podcast_id):
    """Get a single podcast by ID"""
    try:
        podcast = db.session.get(Podcast, podcast_id)
        
        if not podcast:
            return jsonify({
                'success': False,
                'message': 'Podcast not found'
            }), 404
        
        return jsonify({
            'success': True,
            'podcast': podcast.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.exception('Error fetching podcast')
        return jsonify({
            'success': False,
            'message': f'Error fetching podcast: {str(e)}'
        }), 500


@podcasts_bp.route('', methods=['POST'])
@login_required
@admin_required
def create_podcast():
    """Create a new podcast (Admin only)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('title'):
            return jsonify({
                'success': False,
                'message': 'Title is required'
            }), 400
        
        if not data.get('audio_url'):
            return jsonify({
                'success': False,
                'message': 'Audio URL is required'
            }), 400
        
        # Create new podcast
        podcast = Podcast(
            title=data['title'],
            description=data.get('description'),
            guest=data.get('guest'),
            audio_url=data['audio_url'],
            thumbnail_url=data.get('thumbnail_url'),
            duration=data.get('duration'),
            episode_number=data.get('episode_number'),
            season_number=data.get('season_number'),
            category=data.get('category'),
            tags=data.get('tags', []),
            published=data.get('published', False),
            created_by=current_user.user_id
        )
        
        # Set published_at if publishing
        if podcast.published:
            podcast.published_at = datetime.now(timezone.utc)
        
        db.session.add(podcast)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Podcast created successfully',
            'podcast': podcast.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Error creating podcast')
        return jsonify({
            'success': False,
            'message': f'Error creating podcast: {str(e)}'
        }), 500


@podcasts_bp.route('/<int:podcast_id>', methods=['PUT'])
@login_required
@admin_required
def update_podcast(podcast_id):
    """Update a podcast (Admin only)"""
    try:
        podcast = db.session.get(Podcast, podcast_id)
        
        if not podcast:
            return jsonify({
                'success': False,
                'message': 'Podcast not found'
            }), 404
        
        data = request.get_json()
        
        # Update fields if provided
        if 'title' in data:
            podcast.title = data['title']
        if 'description' in data:
            podcast.description = data['description']
        if 'guest' in data:
            podcast.guest = data['guest']
        if 'audio_url' in data:
            podcast.audio_url = data['audio_url']
        if 'thumbnail_url' in data:
            podcast.thumbnail_url = data['thumbnail_url']
        if 'duration' in data:
            podcast.duration = data['duration']
        if 'episode_number' in data:
            podcast.episode_number = data['episode_number']
        if 'season_number' in data:
            podcast.season_number = data['season_number']
        if 'category' in data:
            podcast.category = data['category']
        if 'tags' in data:
            podcast.tags = data['tags']
        if 'published' in data:
            was_published = podcast.published
            podcast.published = data['published']
            
            # Set published_at when first publishing
            if not was_published and podcast.published:
                podcast.published_at = datetime.now(timezone.utc)
        
        podcast.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Podcast updated successfully',
            'podcast': podcast.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Error updating podcast')
        return jsonify({
            'success': False,
            'message': f'Error updating podcast: {str(e)}'
        }), 500


@podcasts_bp.route('/<int:podcast_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_podcast(podcast_id):
    """Delete a podcast (Admin only)"""
    try:
        podcast = db.session.get(Podcast, podcast_id)
        
        if not podcast:
            return jsonify({
                'success': False,
                'message': 'Podcast not found'
            }), 404
        
        db.session.delete(podcast)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Podcast deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Error deleting podcast')
        return jsonify({
            'success': False,
            'message': f'Error deleting podcast: {str(e)}'
        }), 500


@podcasts_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get all unique podcast categories"""
    try:
        categories = db.session.query(Podcast.category)\
            .filter(Podcast.category.isnot(None))\
            .distinct()\
            .all()
        
        category_list = [cat[0] for cat in categories]
        
        return jsonify({
            'success': True,
            'categories': category_list
        }), 200
        
    except Exception as e:
        current_app.logger.exception('Error fetching podcast categories')
        return jsonify({
            'success': False,
            'message': f'Error fetching categories: {str(e)}'
        }), 500


@podcasts_bp.route('/stats', methods=['GET'])
@login_required
@admin_required
def get_stats():
    """Get podcast statistics (Admin only)"""
    try:
        total = Podcast.query.count()
        published = Podcast.query.filter_by(published=True).count()
        draft = Podcast.query.filter_by(published=False).count()
        
        categories = db.session.query(
            Podcast.category, 
            db.func.count(Podcast.podcast_id)
        ).filter(Podcast.category.isnot(None))\
         .group_by(Podcast.category)\
         .all()
        
        category_stats = {cat: count for cat, count in categories}
        
        return jsonify({
            'success': True,
            'stats': {
                'total': total,
                'published': published,
                'draft': draft,
                'by_category': category_stats
            }
        }), 200
        
    except Exception as e:
        current_app.logger.exception('Error fetching podcast stats')
        return jsonify({
            'success': False,
            'message': f'Error fetching stats: {str(e)}'
        }), 500
