from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, DailyAffirmation, AffirmationDelivery, Champion
from decorators import supervisor_required, admin_required
from datetime import datetime, timedelta

affirmations_bp = Blueprint('affirmations', __name__, url_prefix='/api/affirmations')


@affirmations_bp.route('/', methods=['GET'])
@login_required
def list_affirmations():
    """Get all affirmations with optional filtering."""
    theme = request.args.get('theme')
    active_only = request.args.get('active', 'true').lower() == 'true'
    scheduled_date = request.args.get('scheduled_date')
    
    query = DailyAffirmation.query
    
    if theme:
        query = query.filter_by(theme=theme)
    if active_only:
        query = query.filter_by(is_active=True)
    if scheduled_date:
        query = query.filter_by(scheduled_date=datetime.fromisoformat(scheduled_date).date())
    
    query = query.order_by(DailyAffirmation.scheduled_date.desc())
    affirmations = query.all()
    
    return jsonify({
        'success': True,
        'total': len(affirmations),
        'affirmations': [{
            'affirmation_id': a.affirmation_id,
            'content': a.content,
            'theme': a.theme,
            'scheduled_date': a.scheduled_date.isoformat() if a.scheduled_date else None,
            'is_active': a.is_active,
            'times_sent': a.times_sent,
            'created_at': a.created_at.isoformat() if a.created_at else None
        } for a in affirmations]
    }), 200


@affirmations_bp.route('/<int:affirmation_id>', methods=['GET'])
@login_required
def get_affirmation(affirmation_id):
    """Get detailed affirmation including delivery stats."""
    affirmation = DailyAffirmation.query.get_or_404(affirmation_id)
    
    # Get delivery statistics
    deliveries = AffirmationDelivery.query.filter_by(affirmation_id=affirmation_id).all()
    total_sent = len(deliveries)
    total_viewed = sum(1 for d in deliveries if d.viewed_at)
    total_liked = sum(1 for d in deliveries if d.liked_at)
    
    return jsonify({
        'success': True,
        'affirmation': {
            'affirmation_id': affirmation.affirmation_id,
            'content': affirmation.content,
            'theme': affirmation.theme,
            'scheduled_date': affirmation.scheduled_date.isoformat() if affirmation.scheduled_date else None,
            'is_active': affirmation.is_active,
            'times_sent': affirmation.times_sent,
            'created_by': affirmation.created_by,
            'created_at': affirmation.created_at.isoformat() if affirmation.created_at else None,
            'updated_at': affirmation.updated_at.isoformat() if affirmation.updated_at else None,
            'delivery_stats': {
                'total_sent': total_sent,
                'total_viewed': total_viewed,
                'total_liked': total_liked,
                'view_rate': round(total_viewed / total_sent * 100, 1) if total_sent > 0 else 0,
                'like_rate': round(total_liked / total_sent * 100, 1) if total_sent > 0 else 0
            }
        }
    }), 200


@affirmations_bp.route('/', methods=['POST'])
@login_required
@supervisor_required
def create_affirmation():
    """Create a new daily affirmation."""
    data = request.get_json()
    
    if not data.get('content'):
        return jsonify({
            'success': False,
            'message': 'Content is required'
        }), 400
    
    affirmation = DailyAffirmation(
        content=data['content'],
        theme=data.get('theme', 'General'),
        scheduled_date=datetime.fromisoformat(data['scheduled_date']).date() if data.get('scheduled_date') else None,
        is_active=data.get('is_active', True),
        created_by=current_user.user_id
    )
    
    db.session.add(affirmation)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Affirmation created successfully',
        'affirmation_id': affirmation.affirmation_id
    }), 201


@affirmations_bp.route('/<int:affirmation_id>', methods=['PUT'])
@login_required
@supervisor_required
def update_affirmation(affirmation_id):
    """Update an existing affirmation."""
    affirmation = DailyAffirmation.query.get_or_404(affirmation_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    if 'content' in data:
        affirmation.content = data['content']
    if 'theme' in data:
        affirmation.theme = data['theme']
    if 'scheduled_date' in data:
        affirmation.scheduled_date = datetime.fromisoformat(data['scheduled_date']).date() if data['scheduled_date'] else None
    if 'is_active' in data:
        affirmation.is_active = data['is_active']
    
    affirmation.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Affirmation updated successfully'
    }), 200


@affirmations_bp.route('/<int:affirmation_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_affirmation(affirmation_id):
    """Delete an affirmation (admin only)."""
    affirmation = DailyAffirmation.query.get_or_404(affirmation_id)
    
    # Soft delete by deactivating
    affirmation.is_active = False
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Affirmation deactivated successfully'
    }), 200


# Delivery tracking endpoints
@affirmations_bp.route('/deliveries', methods=['GET'])
@login_required
@supervisor_required
def list_deliveries():
    """Get affirmation delivery history."""
    champion_id = request.args.get('champion_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    query = AffirmationDelivery.query
    
    if champion_id:
        query = query.filter_by(champion_id=champion_id)
    if date_from:
        query = query.filter(AffirmationDelivery.delivery_date >= datetime.fromisoformat(date_from).date())
    if date_to:
        query = query.filter(AffirmationDelivery.delivery_date <= datetime.fromisoformat(date_to).date())
    
    query = query.order_by(AffirmationDelivery.delivery_date.desc())
    deliveries = query.all()
    
    return jsonify({
        'success': True,
        'total': len(deliveries),
        'deliveries': [{
            'delivery_id': d.delivery_id,
            'affirmation_id': d.affirmation_id,
            'champion_id': d.champion_id,
            'champion_name': d.champion.full_name if d.champion else None,
            'delivery_date': d.delivery_date.isoformat() if d.delivery_date else None,
            'delivery_method': d.delivery_method,
            'viewed': d.viewed_at is not None,
            'liked': d.liked_at is not None,
            'engagement_time_seconds': d.engagement_time_seconds
        } for d in deliveries]
    }), 200


@affirmations_bp.route('/deliveries', methods=['POST'])
@login_required
@supervisor_required
def create_delivery():
    """Record an affirmation delivery to a champion."""
    data = request.get_json()
    
    required_fields = ['affirmation_id', 'champion_id']
    if not all(field in data for field in required_fields):
        return jsonify({
            'success': False,
            'message': f'Missing required fields: {required_fields}'
        }), 400
    
    # Validate affirmation and champion exist
    affirmation = DailyAffirmation.query.get(data['affirmation_id'])
    champion = Champion.query.get(data['champion_id'])
    
    if not affirmation or not champion:
        return jsonify({
            'success': False,
            'message': 'Affirmation or Champion not found'
        }), 404
    
    delivery = AffirmationDelivery(
        affirmation_id=data['affirmation_id'],
        champion_id=data['champion_id'],
        delivery_method=data.get('delivery_method', 'App Notification')
    )
    
    # Increment times_sent counter
    affirmation.times_sent += 1
    
    db.session.add(delivery)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Delivery recorded successfully',
        'delivery_id': delivery.delivery_id
    }), 201


@affirmations_bp.route('/deliveries/<int:delivery_id>/engagement', methods=['PUT'])
@login_required
def update_engagement(delivery_id):
    """Update engagement metrics for a delivery (viewed/liked)."""
    delivery = AffirmationDelivery.query.get_or_404(delivery_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    if 'viewed' in data and data['viewed'] and not delivery.viewed_at:
        delivery.viewed_at = datetime.utcnow()
    
    if 'liked' in data and data['liked'] and not delivery.liked_at:
        delivery.liked_at = datetime.utcnow()
    
    if 'engagement_time_seconds' in data:
        delivery.engagement_time_seconds = data['engagement_time_seconds']
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Engagement updated successfully'
    }), 200


@affirmations_bp.route('/themes', methods=['GET'])
@login_required
def get_themes():
    """Get list of all affirmation themes."""
    themes = db.session.query(DailyAffirmation.theme).distinct().all()
    theme_list = [t[0] for t in themes if t[0]]
    
    return jsonify({
        'success': True,
        'themes': sorted(theme_list)
    }), 200


@affirmations_bp.route('/schedule/today', methods=['GET'])
@login_required
def get_today_affirmation():
    """Get the affirmation scheduled for today."""
    today = datetime.utcnow().date()
    
    affirmation = DailyAffirmation.query.filter_by(
        scheduled_date=today,
        is_active=True
    ).first()
    
    if not affirmation:
        return jsonify({
            'success': True,
            'message': 'No affirmation scheduled for today',
            'affirmation': None
        }), 200
    
    return jsonify({
        'success': True,
        'affirmation': {
            'affirmation_id': affirmation.affirmation_id,
            'content': affirmation.content,
            'theme': affirmation.theme
        }
    }), 200
