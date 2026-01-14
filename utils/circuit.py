"""Simple in-memory circuit breaker to prevent repeated downstream calls when failing."""
import time
import threading


class CircuitBreaker:
    def __init__(self, fail_max=5, reset_timeout=30):
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self._lock = threading.Lock()
        self._fail_count = 0
        self._last_failure = None

    def call_allowed(self):
        with self._lock:
            if self._fail_count >= self.fail_max:
                # check if reset timeout elapsed
                if (time.time() - (self._last_failure or 0)) > self.reset_timeout:
                    # reset
                    self._fail_count = 0
                    self._last_failure = None
                    return True
                return False
            return True

    def record_success(self):
        with self._lock:
            self._fail_count = 0
            self._last_failure = None

    def record_failure(self):
        with self._lock:
            self._fail_count += 1
            self._last_failure = time.time()


def circuit(fb: CircuitBreaker):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            if not fb.call_allowed():
                raise RuntimeError('CircuitOpen')
            try:
                result = fn(*args, **kwargs)
            except Exception:
                fb.record_failure()
                raise
            else:
                fb.record_success()
                return result
        return wrapper
    return decorator
