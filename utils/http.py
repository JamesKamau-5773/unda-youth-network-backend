"""HTTP helpers: requests Session with retries and sensible timeouts."""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def get_session(retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 503, 504), pool_maxsize=10):
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=frozenset(['GET', 'POST', 'PUT', 'DELETE', 'HEAD'])
    )
    adapter = HTTPAdapter(max_retries=retry, pool_maxsize=pool_maxsize)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session


def request_with_timeout(session, method, url, timeout=10, **kwargs):
    """Wrapper around session.request that applies a default timeout."""
    return session.request(method, url, timeout=timeout, **kwargs)
