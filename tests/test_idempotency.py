import importlib.util
from pathlib import Path

# Load utils/idempotency.py directly to avoid package import issues in test env
spec = importlib.util.spec_from_file_location(
    "idempotency",
    str(Path(__file__).resolve().parents[1] / "utils" / "idempotency.py"),
)
idempotency = importlib.util.module_from_spec(spec)
spec.loader.exec_module(idempotency)


class FakeRedis:
    def __init__(self):
        self.store = {}

    def setnx(self, key, val):
        if key in self.store:
            return False
        self.store[key] = val
        return True

    def expire(self, key, ttl):
        # no-op for fake
        return True

    def get(self, key):
        return self.store.get(key)

    def set(self, key, val, ex=None):
        self.store[key] = val
        return True


def setup_function(fn):
    # Replace the real Redis client with a fresh fake for each test
    idempotency._r = FakeRedis()


def test_make_key_is_deterministic():
    k1 = idempotency.make_key_from_args(42, '254712345678', 500, 'REF')
    k2 = idempotency.make_key_from_args(42, '254712345678', 500, 'REF')
    assert k1 == k2


def test_reserve_and_update_and_get():
    key = 'testkey'
    assert idempotency.reserve_key(key, meta={'a': 1}) is True
    entry = idempotency.get_key(key)
    assert entry is not None
    assert entry['status'] == 'pending'

    idempotency.update_key(key, status='success', response={'ok': True})
    entry2 = idempotency.get_key(key)
    assert entry2['status'] == 'success'
    assert entry2['response'] == {'ok': True}


def test_reserve_conflict():
    key = 'conflict'
    assert idempotency.reserve_key(key) is True
    # second reservation should fail
    assert idempotency.reserve_key(key) is False
