import threading
import time
import importlib.util
from pathlib import Path

# Load idempotency module by path
spec = importlib.util.spec_from_file_location(
    "idempotency",
    str(Path(__file__).resolve().parents[1] / "utils" / "idempotency.py"),
)
idemp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(idemp)


class ThreadSafeFakeRedis:
    def __init__(self):
        self.store = {}
        import threading
        self.lock = threading.Lock()

    def setnx(self, key, val):
        with self.lock:
            if key in self.store:
                return False
            self.store[key] = val
            return True

    def expire(self, key, ttl):
        return True

    def get(self, key):
        with self.lock:
            return self.store.get(key)

    def set(self, key, val, ex=None):
        with self.lock:
            self.store[key] = val
            return True


def test_concurrent_reserve_only_one_wins():
    idemp._r = ThreadSafeFakeRedis()
    key = 'concurrent-test-key'

    results = []

    def attempt():
        ok = idemp.reserve_key(key)
        results.append(ok)

    threads = [threading.Thread(target=attempt) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sum(1 for r in results if r) == 1
