from models import db, UMVGlobalEntry


def create_umv_entry(key: str, value) -> UMVGlobalEntry:
    key = (key or '').strip()
    if not key:
        raise ValueError('Key is required')
    entry = UMVGlobalEntry(key=key, value=value)
    db.session.add(entry)
    db.session.commit()
    return entry


def update_umv_entry(entry_id: int, key: str, value) -> UMVGlobalEntry:
    entry = db.session.get(UMVGlobalEntry, entry_id)
    if not entry:
        raise ValueError('UMV entry not found')
    entry.key = key or entry.key
    entry.value = value
    db.session.commit()
    return entry


def delete_umv_entry(entry_id: int) -> None:
    entry = db.session.get(UMVGlobalEntry, entry_id)
    if not entry:
        raise ValueError('UMV entry not found')
    db.session.delete(entry)
    db.session.commit()


def list_umv_entries():
    return db.session.query(UMVGlobalEntry).order_by(UMVGlobalEntry.key.asc()).all()
