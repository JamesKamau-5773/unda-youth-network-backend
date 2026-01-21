import os
import json
import hashlib
from datetime import datetime, timezone
import redis
from typing import Optional, Dict, Any
from prometheus_client import Counter

# Prometheus metrics for idempotency events (created lazily to avoid duplicate registration)
IDEMP_REQUESTS = None
IDEMP_RESERVED = None
IDEMP_DUPLICATES = None
IDEMP_SUCCESS = None
IDEMP_FAILED = None


def _ensure_metrics():
    global IDEMP_REQUESTS, IDEMP_RESERVED, IDEMP_DUPLICATES, IDEMP_SUCCESS, IDEMP_FAILED
    if IDEMP_REQUESTS is not None:
        return
    try:
        IDEMP_REQUESTS = Counter('idempotency_requests_total', 'Total idempotency requests')
        IDEMP_RESERVED = Counter('idempotency_reserved_total', 'Total idempotency keys successfully reserved')
        IDEMP_DUPLICATES = Counter('idempotency_duplicate_total', 'Total duplicate idempotency attempts')
        IDEMP_SUCCESS = Counter('idempotency_success_total', 'Total idempotency successful responses')
        IDEMP_FAILED = Counter('idempotency_failed_total', 'Total idempotency failed responses')
    except ValueError:
        # Metrics already registered (e.g., tests re-importing modules); ignore
        try:
            from prometheus_client import REGISTRY
            # Attempt to find previously registered collectors by name
            for name in ('idempotency_requests_total', 'idempotency_reserved_total', 'idempotency_duplicate_total', 'idempotency_success_total', 'idempotency_failed_total'):
                # No public API to fetch collectors; skip and leave as None
                pass
        except Exception:
            pass

# Simple Redis-backed idempotency utilities.
# Uses a JSON value stored at key `idemp:{idempotency_key}` with fields:
# {status: 'pending'|'success'|'failed', created_at, updated_at, response, meta}

_redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
_r = redis.from_url(_redis_url, decode_responses=True)

def _redis_key(key: str) -> str:
    return f"idemp:{key}"

def make_key_from_args(user_id: int, phone: str, amount: int, account_ref: str) -> str:
    payload = f"{user_id}:{phone}:{amount}:{account_ref}"
    return hashlib.sha256(payload.encode()).hexdigest()

def reserve_key(key: str, meta: dict = None, ttl: int = 60 * 60 * 24) -> bool:
    """Attempt to reserve an idempotency key. Returns True if reserver wins.

    If reserved, an entry with status 'pending' is created with provided meta.
    """
    rkey = _redis_key(key)
    now = datetime.now(timezone.utc).isoformat()
    value = {
        'status': 'pending',
        'created_at': now,
        'updated_at': now,
        'response': None,
        'meta': meta or {}
    }
    # setnx: only set if not exists
    try:
        _ensure_metrics()
        if IDEMP_REQUESTS:
            IDEMP_REQUESTS.inc()
    except Exception:
        pass
    was_set = _r.setnx(rkey, json.dumps(value))
    if was_set:
        _r.expire(rkey, ttl)
        try:
            if IDEMP_RESERVED:
                IDEMP_RESERVED.inc()
        except Exception:
            pass
    else:
        # Duplicate attempt detected
        try:
            _ensure_metrics()
            if IDEMP_DUPLICATES:
                IDEMP_DUPLICATES.inc()
        except Exception:
            pass
    return was_set

def get_key(key: str) -> Optional[dict]:
    rkey = _redis_key(key)
    raw = _r.get(rkey)
    try:
        _ensure_metrics()
        if IDEMP_REQUESTS:
            IDEMP_REQUESTS.inc()
    except Exception:
        pass
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None

def update_key(key: str, *, status: str, response: Optional[Dict[str, Any]] = None, meta: Optional[Dict[str, Any]] = None, ttl: int = 60 * 60 * 24) -> None:
    rkey = _redis_key(key)
    now = datetime.now(timezone.utc).isoformat()
    entry = get_key(key) or {}
    entry.update({
        'status': status,
        'updated_at': now,
        'response': response,
    })
    if meta:
        entry.setdefault('meta', {}).update(meta)
    # overwrite
    _r.set(rkey, json.dumps(entry), ex=ttl)
    # Update metrics
    try:
        _ensure_metrics()
        if status == 'success' and IDEMP_SUCCESS:
            IDEMP_SUCCESS.inc()
        elif status == 'failed' and IDEMP_FAILED:
            IDEMP_FAILED.inc()
    except Exception:
        pass
