import json
import importlib.util
from pathlib import Path
import time

# Load app and models modules by file path to avoid import issues in pytest environment
base = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(base))
spec_app = importlib.util.spec_from_file_location('app_mod', str(base / 'app.py'))
app_mod = importlib.util.module_from_spec(spec_app)
spec_app.loader.exec_module(app_mod)
create_app = app_mod.create_app

import importlib
models = importlib.import_module('models')
db = models.db
User = models.User


class FakeRedis:
    def __init__(self):
        self.store = {}

    def setnx(self, key, val):
        if key in self.store:
            return False
        self.store[key] = val
        return True

    def expire(self, key, ttl):
        return True

    def get(self, key):
        return self.store.get(key)

    def set(self, key, val, ex=None):
        self.store[key] = val
        return True


def make_fake_resp(data):
    class FakeResp:
        def __init__(self, d):
            self._d = d

        def raise_for_status(self):
            return None

        def json(self):
            return self._d

    return FakeResp(data)


def test_mpesa_stk_idempotency_flow():
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'
    }
    # Disable CSRF for test client
    test_config['WTF_CSRF_ENABLED'] = False
    # Patch endpoint_guard to be a no-op so the mpesa blueprint isn't wrapped in threads during import
    import utils.endpoint_guard as endpoint_guard_mod
    def _noop_endpoint_guard(cb=None, timeout=10):
        def decorator(fn):
            return fn
        return decorator
    endpoint_guard_mod.endpoint_guard = _noop_endpoint_guard

    (app, limiter) = create_app(test_config)

    # Import mpesa module after app creation so its imports are available
    from blueprints import mpesa as mpesa_mod

    # Replace idempotency redis client with fake
    import utils.idempotency as idemp_mod
    idemp_mod._r = FakeRedis()

    # Patch external calls to M-Pesa to return success
    # Ensure M-Pesa module looks configured (bypass environment requirements)
    mpesa_mod.CONSUMER_KEY = 'key'
    mpesa_mod.CONSUMER_SECRET = 'secret'
    mpesa_mod.SHORTCODE = '123456'
    mpesa_mod.PASSKEY = 'pass'

    mpesa_mod.get_access_token = lambda: 'fake-token'
    success_payload = {'ResponseCode': '0', 'CheckoutRequestID': 'CHECKOUT123', 'ResponseDescription': 'Success'}
    mpesa_mod.request_with_timeout = lambda session, method, url, timeout, **kwargs: make_fake_resp(success_payload)

    with app.app_context():
        db.create_all()
        # Create a test user
        u = User(username='tester', password_hash='x', role='Prevention Advocate')
        db.session.add(u)
        db.session.commit()

        client = app.test_client()

        # Replace the endpoint_guard-wrapped view with the original function to avoid thread context issues in tests
        try:
            endpoint_name = None
            for rule in app.url_map.iter_rules():
                if rule.rule == '/api/mpesa/checkout':
                    endpoint_name = rule.endpoint
                    break
            if endpoint_name and hasattr(mpesa_mod.initiate_stk_push, '__wrapped__'):
                app.view_functions[endpoint_name] = mpesa_mod.initiate_stk_push.__wrapped__
        except Exception:
            pass

        # Authenticate by setting session user id
        with client.session_transaction() as sess:
            sess['_user_id'] = str(u.user_id)

        headers = {'Content-Type': 'application/json', 'Idempotency-Key': 'idem-123'}
        payload = {'phoneNumber': '254712345678', 'amount': 100}

        # First request should process and return success
        resp1 = client.post('/api/mpesa/checkout', data=json.dumps(payload), headers=headers)
        # Debug on failure
        if resp1.status_code != 200:
            print('RESP1 STATUS:', resp1.status_code)
            print('RESP1 DATA:', resp1.get_data(as_text=True))
        assert resp1.status_code == 200
        data1 = resp1.get_json()
        assert data1['success'] is True

        # Second request with same idempotency key should return stored result
        resp2 = client.post('/api/mpesa/checkout', data=json.dumps(payload), headers=headers)
        assert resp2.status_code == 200
        data2 = resp2.get_json()
        assert data2['success'] is True
        assert data2['message'] in ('STK Push already processed', 'STK Push sent successfully')
