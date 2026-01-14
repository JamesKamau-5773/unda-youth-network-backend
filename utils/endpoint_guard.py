import functools
import concurrent.futures
from flask import jsonify, copy_current_request_context


def endpoint_guard(cb=None, timeout=10):
    """Decorator to guard endpoint execution with a timeout and optional circuit breaker.

    - cb: CircuitBreaker instance (optional). If provided, requests will be rejected when circuit is open.
    - timeout: seconds to wait for the handler to complete before returning 504.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if cb and not cb.call_allowed():
                return jsonify({'success': False, 'message': 'Service temporarily unavailable.'}), 503

            # Run handler in a short-lived thread to enforce a hard timeout
            # Preserve the Flask request context for the worker thread so
            # handlers that access `request` or other context locals work
            # correctly during tests and normal execution.
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            worker_fn = copy_current_request_context(fn)
            future = executor.submit(worker_fn, *args, **kwargs)
            try:
                result = future.result(timeout=timeout)
                return result
            except concurrent.futures.TimeoutError:
                if cb:
                    try:
                        cb.record_failure()
                    except Exception:
                        pass
                return jsonify({'success': False, 'message': 'Request timed out.'}), 504
            except Exception as e:
                if cb:
                    try:
                        cb.record_failure()
                    except Exception:
                        pass
                raise
            finally:
                try:
                    executor.shutdown(wait=False)
                except Exception:
                    pass

        return wrapper
    return decorator
