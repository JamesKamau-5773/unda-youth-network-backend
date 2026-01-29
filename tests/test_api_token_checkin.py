import os
import sys
import json
import tempfile

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app
from models import db, Champion


def test_token_checkin():
    os.environ['API_SMOKE_TOKEN'] = 'testtoken123'
    result = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
    app = result[0] if isinstance(result, tuple) else result

    with app.app_context():
        db.create_all()
        # create a champion to reference (supply required fields)
        c = Champion(full_name='Token Champion', gender='Other', phone_number='0700000000', assigned_champion_code='TC-1')
        db.session.add(c)
        db.session.commit()

        client = app.test_client()
        payload = {
            'champion_id': c.champion_id,
            'reporting_period': '2026-01-01',
            'number_of_youth_under_support': 5,
            'weekly_check_in_completion_rate': 80
        }

        rv = client.post('/api/checkin', json=payload, headers={'Authorization': 'Bearer testtoken123'})
        assert rv.status_code == 201, rv.data[:200]
        data = rv.get_json()
        assert data.get('success') is True
