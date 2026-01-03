from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, SymbolicItem, ItemDistribution, Champion, TrainingRecord
from decorators import supervisor_required, admin_required
from datetime import datetime

symbolic_items_bp = Blueprint('symbolic_items', __name__, url_prefix='/api/symbolic-items')


@symbolic_items_bp.route('/', methods=['GET'])
@login_required
def list_items():
    """Get all symbolic items with optional filtering."""
    item_type = request.args.get('type')
    linked_to = request.args.get('linked_to')  # Filter by linked training module
    in_stock = request.args.get('in_stock', 'false').lower() == 'true'
    
    query = SymbolicItem.query
    
    if item_type:
        query = query.filter_by(item_type=item_type)
    if linked_to:
        query = query.filter_by(linked_to_training_module=linked_to)
    if in_stock:
        query = query.filter(SymbolicItem.total_quantity > SymbolicItem.distributed_quantity)
    
    query = query.order_by(SymbolicItem.item_name.asc())
    items = query.all()
    
    return jsonify({
        'success': True,
        'total': len(items),
        'items': [i.to_dict() for i in items]
    }), 200


@symbolic_items_bp.route('/<int:item_id>', methods=['GET'])
@login_required
def get_item(item_id):
    """Get detailed item information including distribution history."""
    item = SymbolicItem.query.get_or_404(item_id)
    
    distributions = ItemDistribution.query.filter_by(item_id=item_id).order_by(
        ItemDistribution.distributed_at.desc()
    ).all()
    
    return jsonify({
        'success': True,
        'item': {
            'item_id': item.item_id,
            'item_name': item.item_name,
            'item_type': item.item_type,
            'description': item.description,
            'linked_to_training_module': item.linked_to_training_module,
            'total_quantity': item.total_quantity,
            'distributed_quantity': item.distributed_quantity,
            'available_quantity': item.total_quantity - item.distributed_quantity,
            'is_active': item.is_active,
            'created_at': item.created_at.isoformat() if item.created_at else None,
            'recent_distributions': [{
                'distribution_id': d.distribution_id,
                'champion_id': d.champion_id,
                'champion_name': d.champion.full_name if d.champion else None,
                'distributed_at': d.distributed_at.isoformat() if d.distributed_at else None,
                'distribution_reason': d.distribution_reason
            } for d in distributions[:10]]  # Last 10 distributions
        }
    }), 200


@symbolic_items_bp.route('/', methods=['POST'])
@login_required
@admin_required
def create_item():
    """Create a new symbolic item (admin only)."""
    data = request.get_json()
    
    required_fields = ['item_name', 'item_type', 'total_quantity']
    if not all(field in data for field in required_fields):
        return jsonify({
            'success': False,
            'message': f'Missing required fields: {required_fields}'
        }), 400
    
    item = SymbolicItem(
        item_name=data['item_name'],
        item_type=data['item_type'],
        description=data.get('description'),
        linked_to_training_module=data.get('linked_to_training_module'),
        total_quantity=data['total_quantity'],
        is_active=data.get('is_active', True)
    )
    
    db.session.add(item)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Symbolic item created successfully',
        'item_id': item.item_id
    }), 201


@symbolic_items_bp.route('/<int:item_id>', methods=['PUT'])
@login_required
@admin_required
def update_item(item_id):
    """Update symbolic item details (admin only)."""
    item = SymbolicItem.query.get_or_404(item_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    if 'item_name' in data:
        item.item_name = data['item_name']
    if 'item_type' in data:
        item.item_type = data['item_type']
    if 'description' in data:
        item.description = data['description']
    if 'linked_to_training_module' in data:
        item.linked_to_training_module = data['linked_to_training_module']
    if 'total_quantity' in data:
        item.total_quantity = data['total_quantity']
    if 'is_active' in data:
        item.is_active = data['is_active']
    
    item.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Symbolic item updated successfully'
    }), 200


@symbolic_items_bp.route('/<int:item_id>/restock', methods=['POST'])
@login_required
@admin_required
def restock_item(item_id):
    """Add more quantity to an item's inventory."""
    item = SymbolicItem.query.get_or_404(item_id)
    data = request.get_json()
    
    if not data.get('quantity') or data['quantity'] <= 0:
        return jsonify({
            'success': False,
            'message': 'Valid quantity is required'
        }), 400
    
    item.total_quantity += data['quantity']
    item.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Added {data["quantity"]} items to inventory',
        'new_total': item.total_quantity,
        'available': item.total_quantity - item.distributed_quantity
    }), 200


# Distribution endpoints
@symbolic_items_bp.route('/distributions', methods=['GET'])
@login_required
@supervisor_required
def list_distributions():
    """Get all item distributions with optional filtering."""
    champion_id = request.args.get('champion_id', type=int)
    item_id = request.args.get('item_id', type=int)
    date_from = request.args.get('date_from')
    
    query = ItemDistribution.query
    
    if champion_id:
        query = query.filter_by(champion_id=champion_id)
    if item_id:
        query = query.filter_by(item_id=item_id)
    if date_from:
        query = query.filter(ItemDistribution.distributed_at >= datetime.fromisoformat(date_from))
    
    query = query.order_by(ItemDistribution.distributed_at.desc())
    distributions = query.all()
    
    return jsonify({
        'success': True,
        'total': len(distributions),
        'distributions': [{
            'distribution_id': d.distribution_id,
            'item_id': d.item_id,
            'item_name': d.item.item_name if d.item else None,
            'champion_id': d.champion_id,
            'champion_name': d.champion.full_name if d.champion else None,
            'distributed_at': d.distributed_at.isoformat() if d.distributed_at else None,
            'distribution_reason': d.distribution_reason,
            'linked_training_record_id': d.linked_training_record_id,
            'linked_event_participation_id': d.linked_event_participation_id
        } for d in distributions]
    }), 200


@symbolic_items_bp.route('/distributions', methods=['POST'])
@login_required
@supervisor_required
def distribute_item():
    """Distribute an item to a champion."""
    data = request.get_json()
    
    required_fields = ['item_id', 'champion_id', 'distribution_reason']
    if not all(field in data for field in required_fields):
        return jsonify({
            'success': False,
            'message': f'Missing required fields: {required_fields}'
        }), 400
    
    # Validate item and champion exist
    item = SymbolicItem.query.get(data['item_id'])
    champion = Champion.query.get(data['champion_id'])
    
    if not item or not champion:
        return jsonify({
            'success': False,
            'message': 'Item or Champion not found'
        }), 404
    
    # Check if item is available
    available = item.total_quantity - item.distributed_quantity
    if available <= 0:
        return jsonify({
            'success': False,
            'message': 'Item is out of stock'
        }), 400
    
    # Validate linked records if provided
    if data.get('linked_training_record_id'):
        training = TrainingRecord.query.get(data['linked_training_record_id'])
        if not training or training.champion_id != data['champion_id']:
            return jsonify({
                'success': False,
                'message': 'Invalid training record or champion mismatch'
            }), 400
    
    distribution = ItemDistribution(
        item_id=data['item_id'],
        champion_id=data['champion_id'],
        distribution_reason=data['distribution_reason'],
        linked_training_record_id=data.get('linked_training_record_id'),
        linked_event_participation_id=data.get('linked_event_participation_id'),
        distributed_by=current_user.user_id
    )
    
    # Update item distributed count
    item.distributed_quantity += 1
    
    # If linked to training, update training record
    if data.get('linked_training_record_id'):
        training = TrainingRecord.query.get(data['linked_training_record_id'])
        training.symbolic_item_received = True
        training.symbolic_item_type = item.item_name
        training.symbolic_item_date = datetime.utcnow().date()
    
    db.session.add(distribution)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Item distributed successfully',
        'distribution_id': distribution.distribution_id,
        'remaining_stock': item.total_quantity - item.distributed_quantity
    }), 201


@symbolic_items_bp.route('/distributions/<int:distribution_id>', methods=['DELETE'])
@login_required
@admin_required
def revoke_distribution(distribution_id):
    """Revoke an item distribution (admin only)."""
    distribution = ItemDistribution.query.get_or_404(distribution_id)
    
    # Update item inventory
    item = distribution.item
    item.distributed_quantity -= 1
    
    # Update training record if linked
    if distribution.linked_training_record_id:
        training = TrainingRecord.query.get(distribution.linked_training_record_id)
        if training:
            training.symbolic_item_received = False
            training.symbolic_item_type = None
            training.symbolic_item_date = None
    
    db.session.delete(distribution)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Distribution revoked successfully'
    }), 200


@symbolic_items_bp.route('/champion/<int:champion_id>/items', methods=['GET'])
@login_required
def get_champion_items(champion_id):
    """Get all symbolic items received by a champion."""
    # Allow champions to view their own items, supervisors to view all
    if current_user.role not in ['Admin', 'Supervisor']:
        if not hasattr(current_user, 'champion') or current_user.champion.champion_id != champion_id:
            return jsonify({
                'success': False,
                'message': 'Unauthorized'
            }), 403
    
    distributions = ItemDistribution.query.filter_by(
        champion_id=champion_id
    ).order_by(ItemDistribution.distributed_at.desc()).all()
    
    return jsonify({
        'success': True,
        'champion_id': champion_id,
        'total_items_received': len(distributions),
        'items': [{
            'distribution_id': d.distribution_id,
            'item_name': d.item.item_name if d.item else None,
            'item_type': d.item.item_type if d.item else None,
            'received_at': d.distributed_at.isoformat() if d.distributed_at else None,
            'reason': d.distribution_reason,
            'linked_to_training': d.linked_training_record_id is not None,
            'linked_to_event': d.linked_event_participation_id is not None
        } for d in distributions]
    }), 200


@symbolic_items_bp.route('/types', methods=['GET'])
@login_required
def get_item_types():
    """Get list of all item types."""
    types = db.session.query(SymbolicItem.item_type).distinct().all()
    type_list = [t[0] for t in types if t[0]]
    
    return jsonify({
        'success': True,
        'types': sorted(type_list)
    }), 200


@symbolic_items_bp.route('/inventory/summary', methods=['GET'])
@login_required
@supervisor_required
def get_inventory_summary():
    """Get inventory summary statistics."""
    items = SymbolicItem.query.filter_by(is_active=True).all()
    
    total_items = len(items)
    total_stock = sum(i.total_quantity for i in items)
    total_distributed = sum(i.distributed_quantity for i in items)
    total_available = total_stock - total_distributed
    
    out_of_stock = sum(1 for i in items if i.total_quantity <= i.distributed_quantity)
    low_stock = sum(1 for i in items if 0 < (i.total_quantity - i.distributed_quantity) <= 5)
    
    return jsonify({
        'success': True,
        'summary': {
            'total_item_types': total_items,
            'total_stock': total_stock,
            'total_distributed': total_distributed,
            'total_available': total_available,
            'distribution_rate': round(total_distributed / total_stock * 100, 1) if total_stock > 0 else 0,
            'out_of_stock_items': out_of_stock,
            'low_stock_items': low_stock
        }
    }), 200
