"""
Custom Prometheus metrics for UNDA Youth Network
Tracks user activity, role-based metrics, and business KPIs
"""

from prometheus_client import Counter, Histogram, Gauge, Info
from flask_login import current_user
from functools import wraps

# Request counters by role
requests_by_role = Counter(
    'unda_requests_by_role_total',
    'Total requests grouped by user role',
    ['role', 'endpoint']
)

# Login metrics
login_attempts = Counter(
    'unda_login_attempts_total',
    'Total login attempts',
    ['status']  # success or failure
)

# Champion metrics
champion_reports_submitted = Counter(
    'unda_champion_reports_submitted_total',
    'Total champion reports submitted'
)

# Supervisor metrics
supervisor_reviews = Counter(
    'unda_supervisor_reviews_total',
    'Total supervisor reviews performed',
    ['action']  # update_notes, update_safeguarding, etc.
)

# Admin metrics
admin_actions = Counter(
    'unda_admin_actions_total',
    'Total admin actions performed',
    ['action']  # create_champion, assign_supervisor, etc.
)

# Active users gauge
active_users = Gauge(
    'unda_active_users',
    'Currently active users',
    ['role']
)

# Database metrics
database_records = Gauge(
    'unda_database_records',
    'Total database records',
    ['table']
)

# Response time by endpoint
endpoint_response_time = Histogram(
    'unda_endpoint_response_seconds',
    'Response time for endpoints',
    ['endpoint', 'method']
)


def track_role_request(endpoint_name):
    """Decorator to track requests by user role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_user.is_authenticated:
                role = current_user.role or 'Unknown'
                requests_by_role.labels(role=role, endpoint=endpoint_name).inc()
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def track_login_attempt(success=True):
    """Track login attempt"""
    status = 'success' if success else 'failure'
    login_attempts.labels(status=status).inc()


def track_champion_report():
    """Track champion report submission"""
    champion_reports_submitted.inc()


def track_supervisor_action(action):
    """Track supervisor action"""
    supervisor_reviews.labels(action=action).inc()


def track_admin_action(action):
    """Track admin action"""
    admin_actions.labels(action=action).inc()


def update_active_users(role, count):
    """Update active users gauge"""
    active_users.labels(role=role).set(count)


def update_database_metrics(db_session):
    """Update database record counts"""
    from models import User, Champion, YouthSupport, RefferalPathway
    
    try:
        database_records.labels(table='users').set(db_session.query(User).count())
        database_records.labels(table='champions').set(db_session.query(Champion).count())
        database_records.labels(table='youth_support').set(db_session.query(YouthSupport).count())
        database_records.labels(table='referrals').set(db_session.query(RefferalPathway).count())
    except Exception:
        pass  # Ignore errors during metric updates
