from typing import Optional
from models import db, User, Champion


def assign_champion(champion_id: int, supervisor_id: int) -> dict:
    champ = db.session.get(Champion, champion_id)
    if not champ:
        raise ValueError('Champion not found')

    supervisor = db.session.get(User, supervisor_id)
    if not supervisor or getattr(supervisor, 'role', None) != 'Supervisor':
        raise ValueError('Invalid supervisor selected')

    old_supervisor_id = champ.supervisor_id
    old_supervisor_name: Optional[str] = None
    if old_supervisor_id:
        old_sup = db.session.get(User, old_supervisor_id)
        if old_sup:
            old_supervisor_name = old_sup.username

    champ.supervisor_id = supervisor_id
    db.session.commit()

    return {
        'old_supervisor_name': old_supervisor_name,
        'new_supervisor_name': supervisor.username,
        'assigned_champion_code': getattr(champ, 'assigned_champion_code', None),
    }


def unassign_champion(champion_id: int) -> dict:
    champ = db.session.get(Champion, champion_id)
    if not champ:
        raise ValueError('Champion not found')

    old_supervisor_name: Optional[str] = None
    if champ.supervisor_id:
        old_sup = db.session.get(User, champ.supervisor_id)
        if old_sup:
            old_supervisor_name = old_sup.username

    champ.supervisor_id = None
    db.session.commit()

    return {
        'old_supervisor_name': old_supervisor_name,
        'assigned_champion_code': getattr(champ, 'assigned_champion_code', None),
    }
