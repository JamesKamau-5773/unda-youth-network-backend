from datetime import datetime, timezone
from models import db, SymbolicItem


def create_symbolic_item(data: dict) -> SymbolicItem:
    item_name = (data.get('item_name') or '').strip()
    item_type = data.get('item_type')
    description = data.get('description')
    total_quantity = int(data.get('total_quantity') or 0)

    if not item_name:
        raise ValueError('Item name is required')

    item = SymbolicItem(item_name=item_name, item_type=item_type, description=description, total_quantity=total_quantity)
    db.session.add(item)
    db.session.commit()
    return item


def update_symbolic_item(item_id: int, data: dict) -> SymbolicItem:
    item = db.session.get(SymbolicItem, item_id)
    if not item:
        raise ValueError('Symbolic item not found')
    item.item_name = data.get('item_name', item.item_name)
    item.item_type = data.get('item_type', item.item_type)
    item.description = data.get('description', item.description)
    if 'total_quantity' in data:
        item.total_quantity = int(data.get('total_quantity') or item.total_quantity)
    item.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return item


def delete_symbolic_item(item_id: int) -> None:
    item = db.session.get(SymbolicItem, item_id)
    if not item:
        raise ValueError('Symbolic item not found')
    db.session.delete(item)
    db.session.commit()


def list_symbolic_items():
    return db.session.query(SymbolicItem).order_by(SymbolicItem.created_at.desc()).all()
