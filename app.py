from models import db, User, Champion
import os
from flask import Flask, redirect, url_for, flash, request, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_cors import CORS
from extensions import limiter
from email_utils import init_mail
from dotenv import load_dotenv
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from prometheus_flask_exporter import PrometheusMetrics

load_dotenv()

# Import models to ensure they are registered with SQLAlchemy


def create_app(test_config=None):
    app = Flask(__name__)
    # Allow tests to override config early so database settings can be provided via test_config
    if test_config:
        app.config.update(test_config)

    # Apply ProxyFix to respect X-Forwarded headers from proxies (e.g., Render).
    # Enable via PROXY_FIX_ENABLED env var (default: true). Skip in test mode.
    try:
        proxy_fix_enabled = os.environ.get('PROXY_FIX_ENABLED', 'True').lower() in ('1', 'true', 'yes')
    except Exception:
        proxy_fix_enabled = True

    if proxy_fix_enabled and not app.config.get('TESTING'):
        try:
            app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
            app.logger.info('Applied ProxyFix middleware (x_for=1, x_proto=1, x_host=1, x_port=1)')
        except Exception:
            app.logger.exception('Failed to apply ProxyFix middleware')
    
    # Initialize Prometheus metrics
    metrics = PrometheusMetrics(app)
    
    # Track additional custom metrics
    try:
        metrics.info('app_info', 'UNDA Youth Network Application', version='1.0.0')
    except ValueError:
        # Tests may initialize Prometheus multiple times in the same process;
        # ignore duplicate registration errors during test runs.
        pass

    # --- Configuration ---
    # SECRET_KEY is required for production; allow fallback when testing
    secret_key = app.config.get('SECRET_KEY') or os.environ.get('SECRET_KEY')
    if not secret_key:
        if app.config.get('TESTING'):
            # Provide a predictable key for test runs
            secret_key = 'test-secret-key'
        else:
            raise ValueError("SECRET_KEY environment variable must be set")
    app.config['SECRET_KEY'] = secret_key
    
    # Database URI from config or environment
    # Allow forcing a local SQLite fallback even if DATABASE_URL exists
    force_sqlite = os.environ.get('FALLBACK_TO_SQLITE', 'False') == 'True'
    database_url = None
    if force_sqlite:
        # Ensure the instance folder exists for the SQLite file
        try:
            os.makedirs(app.instance_path, exist_ok=True)
        except Exception:
            pass
        if app.config.get('TESTING'):
            database_url = 'sqlite:///:memory:'
        else:
            database_url = 'sqlite:///' + os.path.join(app.instance_path, 'local.db')
    else:
        database_url = app.config.get('SQLALCHEMY_DATABASE_URI') or os.environ.get('DATABASE_URL')

    if not database_url:
        # Allow tests to default to an in-memory SQLite DB when no DATABASE_URL provided
        if app.config.get('TESTING'):
            database_url = 'sqlite:///:memory:'
        else:
            raise ValueError("DATABASE_URL environment variable must be set or provide 'SQLALCHEMY_DATABASE_URI' in test_config or enable FALLBACK_TO_SQLITE")
    
    # Fix for Render/Heroku: they use postgres:// but SQLAlchemy 1.4+ requires postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Database connection pool settings
    # Configure SQLAlchemy engine options. Skip pool sizing for SQLite (used in tests).
    if not database_url.startswith('sqlite'):
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_size': 10,
            'pool_recycle': 3600,
            'pool_pre_ping': True,  # Verify connections before using
            'connect_args': {
                'connect_timeout': 10,  # 10 second connection timeout
                'options': '-c statement_timeout=30000'  # 30 second query timeout
            }
        }
    else:
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}

    # Initialize Sentry for error tracking (production only).
    # Do not initialize Sentry when running tests to avoid network calls/delays.
    sentry_dsn = os.environ.get('SENTRY_DSN')
    if sentry_dsn and not app.config.get('TESTING'):
        try:
            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[FlaskIntegration()],
                traces_sample_rate=1.0,
                profiles_sample_rate=1.0,
                environment=os.environ.get('FLASK_ENV', 'production'),
            )
        except Exception:
            # Ensure Sentry failures don't prevent app startup
            app.logger.exception('Sentry initialization failed; continuing without Sentry')
    
    # Rate limiting storage
    app.config.setdefault('RATELIMIT_STORAGE_URL', os.environ.get(
        'REDIS_URL', 'redis://localhost:6379'))
    
    # Session security settings
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

    # Uploads configuration
    # Default upload folder is `static/uploads` but can be overridden by env
    app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER') or os.path.join(app.root_path, 'static', 'uploads')
    # Ensure uploads dir exists
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    except Exception:
        app.logger.exception('Failed to create upload folder')

    # Max content length (bytes) - default 150MB, override with env as integer
    try:
        app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH') or 150 * 1024 * 1024)
    except Exception:
        app.config['MAX_CONTENT_LENGTH'] = 150 * 1024 * 1024

    # AWS S3 configuration (optional)
    app.config['S3_BUCKET'] = os.environ.get('AWS_S3_BUCKET')
    app.config['S3_REGION'] = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION')
    app.config['S3_ACCESS_KEY'] = os.environ.get('AWS_ACCESS_KEY_ID')
    app.config['S3_SECRET_KEY'] = os.environ.get('AWS_SECRET_ACCESS_KEY')
    # If S3_BUCKET is set, we consider S3 enabled
    app.config['USE_S3'] = bool(app.config.get('S3_BUCKET'))
    
    # WTF-CSRF Protection
    # Disable CSRF checks during tests to simplify API testing and avoid
    # brittle failures in CI/test environments that do not exercise the
    # full cookie/token exchange. Production and development still have
    # CSRF enabled by default.
    if app.config.get('TESTING'):
        app.config['WTF_CSRF_ENABLED'] = False
    else:
        app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_TIME_LIMIT'] = None  # No time limit for CSRF tokens
    
    # Email Configuration
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False') == 'True'
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@unda.org')
    app.config['APP_URL'] = os.environ.get('APP_URL', 'http://127.0.0.1:5000')

    # Feature flags (can be overridden via environment or test_config)
    app.config['USE_MEMBER_PORTAL_FOR_ADVOCATES'] = os.environ.get('USE_MEMBER_PORTAL_FOR_ADVOCATES', 'False')
    app.config['MEMBER_PORTAL_URL'] = os.environ.get('MEMBER_PORTAL_URL', '/member-portal')
    # New theme is opt-out by default now (set ENABLE_NEW_THEME=false to disable)
    app.config['ENABLE_NEW_THEME'] = os.environ.get('ENABLE_NEW_THEME', 'True') == 'True'
    
    # Validate email configuration on startup
    email_config_warnings = []
    if not app.config.get('MAIL_USERNAME'):
        email_config_warnings.append('MAIL_USERNAME not set - email sending will fail')
    if not app.config.get('MAIL_PASSWORD'):
        email_config_warnings.append('MAIL_PASSWORD not set - email sending will fail')
    if not app.config.get('MAIL_DEFAULT_SENDER'):
        email_config_warnings.append('MAIL_DEFAULT_SENDER not set - using fallback')
    
    if email_config_warnings:
        print("\nEMAIL CONFIGURATION WARNINGS:")
        for warning in email_config_warnings:
            print(f"   - {warning}")
        print("   → Set these in your .env file to enable email notifications\n")

    # Allow tests to override config before extensions are initialized
    if test_config:
        app.config.update(test_config)

    # --- Initialization ---
    db.init_app(app)
    # If running with a local SQLite fallback and migrations are intentionally
    # skipped (useful for quick local development), ensure tables exist by
    # creating the schema inside the application's context. This avoids
    # "no such table" OperationalError when the developer used
    # `CLEAN_BREAK_MODE=skip_migrations` and did not run alembic migrations.
    try:
        force_sqlite_local = database_url.startswith('sqlite')
    except Exception:
        force_sqlite_local = False

    # Warn if a developer has enabled the SQLite fallback in non-development
    # environments. Using an ephemeral SQLite file in production will cause
    # data loss on redeploys — surface a clear warning so operators can fix env.
    try:
        fallback_flag = os.environ.get('FALLBACK_TO_SQLITE', 'False') == 'True'
    except Exception:
        fallback_flag = False

    if fallback_flag and os.environ.get('FLASK_ENV') != 'development':
        app.logger.warning('FALLBACK_TO_SQLITE is enabled while FLASK_ENV=%s. This may cause data loss across redeploys.', os.environ.get('FLASK_ENV'))

    # In production, fail-fast if we cannot reach the configured Postgres
    # database. This prevents the application from silently using an
    # ephemeral SQLite DB and losing data on restart.
    if not app.config.get('TESTING') and os.environ.get('FLASK_ENV') == 'production':
        if force_sqlite_local:
            app.logger.error('Configured DATABASE_URL resolves to SQLite in production — aborting startup to avoid data loss.')
            raise RuntimeError('Refusing to start with SQLite fallback in production')
        else:
            try:
                # Run a trivial query to verify connectivity and credentials.
                with app.app_context():
                    from sqlalchemy import text
                    db.session.execute(text('SELECT 1'))
                    db.session.commit()
                    app.logger.info('Database connectivity check passed')
            except Exception as exc:
                app.logger.exception('Database connectivity check failed at startup: %s', str(exc))
                raise RuntimeError('Database connectivity check failed during startup') from exc

    if (not app.config.get('TESTING') and force_sqlite_local
            and os.environ.get('CLEAN_BREAK_MODE') == 'skip_migrations'):
        try:
            with app.app_context():
                db.create_all()
                app.logger.info('SQLite fallback: ensured DB schema with db.create_all()')
        except Exception:
            app.logger.exception('Failed to auto-create SQLite schema; continuing')

    # Support resetting or provisioning an admin account via environment variables
    # This mechanism is intended only for initial bootstrap or emergency recovery
    # in environments without interactive shell access. It is designed to be
    # idempotent, auditable (logs), and conservative: it will prefer an explicit
    # username if provided, otherwise it will target any existing user with the
    # Admin role. The temporary credentials must be rotated after use.
    admin_temp = os.environ.get('ADMIN_TEMP_PASSWORD')
    if admin_temp:
        admin_username = os.environ.get('ADMIN_TEMP_USERNAME', 'admin')
        admin_email = os.environ.get('ADMIN_TEMP_EMAIL', None)
        try:
            with app.app_context():
                # Prefer explicit username match first
                admin = None
                if admin_username:
                    admin = User.query.filter_by(username=admin_username).first()

                # If not found by username, find any user with Admin role
                if not admin:
                    admin = User.query.filter(User.role.ilike('%admin%')).first()

                if admin:
                    # Reset password and unlock account
                    admin.set_password(admin_temp)
                    admin.account_locked = False
                    admin.failed_login_attempts = 0
                    admin.locked_until = None
                    admin.invite_token = None
                    admin.invite_token_expires = None
                    db.session.add(admin)
                    db.session.commit()
                    app.logger.info('Admin provisioning: password reset for user=%s (id=%s)', admin.username, getattr(admin, 'user_id', 'unknown'))
                else:
                    # Create a new admin user with a safe, configured username/email
                    # Ensure we do not accidentally overwrite existing usernames
                    base_username = admin_username or 'admin'
                    username = base_username
                    suffix = 0
                    while User.query.filter_by(username=username).first():
                        suffix += 1
                        username = f"{base_username}{suffix}"

                    email_to_use = admin_email or os.environ.get('ADMIN_TEMP_EMAIL', f'{username}@example.com')
                    new_admin = User(username=username, email=email_to_use)
                    new_admin.set_password(admin_temp)
                    new_admin.set_role(User.ROLE_ADMIN)
                    new_admin.account_locked = False
                    new_admin.failed_login_attempts = 0
                    db.session.add(new_admin)
                    db.session.commit()
                    app.logger.info('Admin provisioning: created admin user=%s (id=%s)', new_admin.username, getattr(new_admin, 'user_id', 'unknown'))
        except Exception:
            # Capture the exception but do not raise; application should continue booting.
            app.logger.exception('Admin provisioning failed while applying ADMIN_TEMP_PASSWORD')
    
    # Initialize Flask-Mail
    # Allow disabling email initialization during build or CI to avoid outbound SMTP calls
    if os.environ.get('DISABLE_EMAIL_IN_BUILD', 'False') == 'True' or os.environ.get('DISABLE_EMAIL', 'False') == 'True':
        app.logger.info('Email initialization skipped (DISABLE_EMAIL_IN_BUILD or DISABLE_EMAIL set)')
    else:
        init_mail(app)
    
    # CORS Configuration - Allow API access from different origins
    cors_origins = os.environ.get('CORS_ORIGINS', '*')  # Use '*' by default
    # Optionally include a single frontend origin (recommended for production)
    # Set FRONTEND_ORIGIN=https://undayouth.org in production to enable
    # credentialed CORS responses for that origin.
    # Prefer an explicit SESSION_COOKIE_DOMAIN env var for cookie domain
    # behaviour. Do NOT auto-derive cookie domain from FRONTEND_ORIGIN; that
    # caused sessions/CSRF to break when admin UI was hosted on a different
    # host. Set SESSION_COOKIE_DOMAIN explicitly in production (e.g.
    # ".undayouth.org").
    session_cookie_domain = os.environ.get('SESSION_COOKIE_DOMAIN')
    frontend_origin = os.environ.get('FRONTEND_ORIGIN')
    if frontend_origin:
        if cors_origins == '*':
            cors_origins = frontend_origin
        elif frontend_origin not in [o.strip() for o in cors_origins.split(',') if o.strip()]:
            cors_origins = cors_origins + ',' + frontend_origin

    if session_cookie_domain:
        app.config['SESSION_COOKIE_DOMAIN'] = session_cookie_domain
    else:
        # Avoid silently deriving a cookie domain which may break web UI.
        if frontend_origin:
            app.logger.info('FRONTEND_ORIGIN set but SESSION_COOKIE_DOMAIN not set; not deriving cookie domain automatically. Set SESSION_COOKIE_DOMAIN to enable cross-subdomain cookies.')

    # Custom origin validation for Netlify preview URLs
    def is_valid_origin(origin):
        if cors_origins == '*':
            return True
        allowed = [o.strip() for o in cors_origins.split(',') if o.strip()]
        # Allow any Netlify subdomain and localhost origins for developer convenience
        if origin and ('netlify.app' in origin or 'localhost' in origin):
            return True
        return origin in allowed

    # If the configured origins is a wildcard, do NOT enable credentialed responses
    # (browsers will reject Access-Control-Allow-Credentials with a wildcard origin).
    # When specific origins are provided via CORS_ORIGINS, enable credentials and
    # set session cookie SameSite=None to allow cross-site cookie usage.
    if cors_origins == '*':
        cors_origins_param = '*'
        cors_supports_credentials = False
    else:
        # Build an explicit list of allowed origins from the env variable.
        # Avoid passing a callable into flask-cors to prevent unexpected
        # iteration behavior in some flask-cors versions.
        allowed = [o.strip() for o in cors_origins.split(',') if o.strip()]
        # Add common local dev origins to ease developer workflows when not
        # explicitly specified in CORS_ORIGINS.
        for dev_origin in ('http://localhost:5173', 'http://localhost:3000', 'http://127.0.0.1:5000'):
            if dev_origin not in allowed:
                allowed.append(dev_origin)

        cors_origins_param = allowed
        cors_supports_credentials = True
        # Allow cross-site cookies when credentialed CORS is enabled
        try:
            # Only set SameSite=None when credentials are explicitly enabled
            app.config['SESSION_COOKIE_SAMESITE'] = 'None'
            # Ensure secure flag is enabled in non-testing environments
            if os.environ.get('FLASK_ENV') == 'production':
                app.config['SESSION_COOKIE_SECURE'] = True
        except Exception:
            pass

    # Enable CORS for API and auth endpoints (and other public routes).
    # Use a broad resource pattern so preflight requests for `/auth/*` and other
    # non-`/api/*` endpoints also receive CORS headers.
    CORS(app, resources={
        r"/*": {
            "origins": cors_origins_param,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "X-CSRFToken"],
            "expose_headers": ["Content-Type", "Authorization"],
            "supports_credentials": cors_supports_credentials,
            "max_age": 3600
        }
    })
    
    # CSRF Protection
    csrf = CSRFProtect(app)
    
    # CSRF error handler
    @app.errorhandler(400)
    def handle_csrf_error(e):
        error_msg = str(e)
        # If this looks like a CSRF-related 400 and the request appears to be
        # from an API client (JSON/XHR), return a concise, user-friendly JSON
        # response instead of an HTML redirect. This prevents the client from
        # receiving an opaque redirect page and makes the error actionable.
        if 'CSRF' in error_msg or 'csrf' in error_msg.lower():
            if is_api_request():
                return jsonify({
                    'error': 'Session expired or security token invalid.',
                    'message': 'Please refresh the page and sign in again. If this keeps happening, contact support.'
                }), 400
            # For normal browser navigations, preserve the existing flash+redirect UX
            flash('Security token expired or invalid. Please try again.', 'danger')
            return redirect(request.url if request.referrer else url_for('admin.dashboard')), 400
        return e
    
    # Global error handlers for common HTTP errors
    @app.errorhandler(403)
    def forbidden(e):
        """Handle 403 Forbidden errors"""
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'error': 'Forbidden',
                'message': 'You do not have permission to access this resource',
                'status': 403
            }), 403
        flash('Access denied. You do not have permission to access this resource.', 'danger')
        return redirect(url_for('auth.login'))
    
    @app.errorhandler(404)
    def not_found(e):
        """Handle 404 Not Found errors"""
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'error': 'Not Found',
                'message': 'The requested resource was not found',
                'status': 404
            }), 404
        flash('The page you are looking for does not exist.', 'warning')
        # Redirect to appropriate dashboard based on user role
        if current_user.is_authenticated:
            role_lower = (current_user.role or '').lower()
            if role_lower == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif role_lower == 'supervisor':
                return redirect(url_for('supervisor.dashboard'))
            elif role_lower in ['champion', 'prevention advocate']:
                # If advocates have been migrated, send them to the frontend member portal
                if os.environ.get('USE_MEMBER_PORTAL_FOR_ADVOCATES', 'False') == 'True':
                    return redirect(os.environ.get('MEMBER_PORTAL_URL', '/member-portal'))
                return redirect(url_for('champion.dashboard'))
        return redirect(url_for('auth.login'))
    
    def is_api_request(req=None):
        """Return True if the request is likely from an API client (JSON/XHR).

        Checks `request.is_json`, the `Accept` header, `X-Requested-With`,
        or if the path starts with `/api/`.
        """
        # If an exception object is passed in by Flask's error handling, fall
        # back to using the global `request` object which has the expected
        # headers and attributes.
        r = request if not getattr(req, 'headers', None) else req
        accept = (getattr(r, 'headers', {}) or {}).get('Accept', '') or ''
        x_requested = (getattr(r, 'headers', {}) or {}).get('X-Requested-With', '') or ''
        return (
            getattr(r, 'is_json', False)
            or getattr(r, 'path', '').startswith('/api/')
            or x_requested == 'XMLHttpRequest'
            or 'application/json' in accept
        )

    @app.errorhandler(429)
    def ratelimit_errorhandler(e):
        """Flask error handler for 429 that delegates to the ratelimit handler.

        Keep the actual response logic separate so helper functions like
        `is_api_request` are not directly used as error handlers (Flask may
        pass exception objects into handlers which can lead to attribute
        access errors).
        """
        return ratelimit_handler(e)

    def ratelimit_handler(e):
        """Handle 429 Too Many Requests (rate limit exceeded)"""
        if is_api_request():
            return jsonify({
                'error': 'Too Many Requests',
                'message': 'Rate limit exceeded. Please try again later.',
                'status': 429
            }), 429
        flash('Too many requests. Please slow down and try again in a few minutes.', 'warning')
        return redirect(request.referrer or url_for('auth.login'))
    
    @app.errorhandler(500)
    def internal_error(e):
        """Handle 500 Internal Server errors"""
        # Log the error for debugging
        app.logger.error(f'Internal Server Error: {str(e)}', exc_info=True)
        
        # Rollback any pending database transactions
        try:
            db.session.rollback()
        except:
            pass
        
        if is_api_request():
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred. Our team has been notified.',
                'status': 500
            }), 500
        
        flash('An unexpected error occurred. Our team has been notified. Please try again later.', 'danger')
        # Safely redirect to login (avoid redirect loops)
        return redirect('/auth/login')

    # Flask-Login setup
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # Define the login route
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    @login_manager.unauthorized_handler
    def unauthorized():
        # For API/XHR requests return JSON 401 instead of redirecting to login page.
        if is_api_request():
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Authentication required',
                'code': 401
            }), 401

        # Prevent redirect loops - directly redirect to login without using url_for in request context
        return redirect('/auth/login')

    # Diagnostic: log the endpoint and whether the view function is marked
    # as CSRF-exempt. This will help identify why CSRFProtect still blocks
    # certain API requests in deployed environments.
    @app.before_request
    def log_endpoint_csrf_status():
        try:
            endpoint = request.endpoint
            vf = app.view_functions.get(endpoint) if endpoint else None
            csrf_flag = False
            if vf:
                csrf_flag = bool(getattr(vf, 'csrf_exempt', False) or getattr(vf, 'exempt', False) or getattr(vf, '_csrf_exempt', False))
            app.logger.info('Request debug: path=%s endpoint=%s csrf_exempt=%s', request.path, endpoint, csrf_flag)
        except Exception:
            app.logger.exception('Failed to log endpoint CSRF status')

    @app.before_request
    def debug_auth_state_for_api():
        # Lightweight diagnostics for API auth issues. Logs only presence of
        # cookies (names) and whether Flask-Login has an authenticated user.
        try:
            if request.path.startswith('/api'):
                cookie_keys = list(request.cookies.keys())
                auth_hdr = bool(request.headers.get('Authorization'))
                is_auth = False
                try:
                    from flask_login import current_user
                    is_auth = bool(current_user and current_user.is_authenticated)
                except Exception:
                    is_auth = False
                app.logger.info('Auth debug: path=%s is_api=True authenticated=%s auth_header=%s cookies=%s',
                                request.path, is_auth, auth_hdr, cookie_keys)
        except Exception:
            app.logger.exception('Failed to log auth debug info')

    # One-time cookie-domain mismatch warning: if `SESSION_COOKIE_DOMAIN` is
    # configured but doesn't appear to cover the incoming request host, log a
    # warning to help triage CSRF/session issues caused by cross-domain cookies.
    @app.before_request
    def warn_cookie_domain_mismatch():
        try:
            cfg = app.config.get('SESSION_COOKIE_DOMAIN')
            if not cfg:
                return
            # Only log once per process startup
            if app.config.get('_COOKIE_DOMAIN_MISMATCH_LOGGED'):
                return
            host = request.host.split(':')[0] if request.host else ''
            # Normalise leading dot
            norm = cfg[1:] if cfg.startswith('.') else cfg
            if host and not (host == norm or host.endswith('.' + norm)):
                app.logger.warning('SESSION_COOKIE_DOMAIN is set to "%s" but request host is "%s" - this may prevent browsers from sending session cookies and cause CSRF/401 errors.', cfg, host)
                app.config['_COOKIE_DOMAIN_MISMATCH_LOGGED'] = True
        except Exception:
            pass

    # Flask-Limiter setup (using Redis for persistent rate limits)
    limiter.init_app(app)
    
    # Security headers
    @app.after_request
    def set_security_headers(response):
        # Content Security Policy - allow Tailwind CDN and inline SVGs
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.tailwindcss.com; font-src 'self' https://fonts.gstatic.com; script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; img-src 'self' data: https:;"
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        # XSS Protection (legacy browsers)
        response.headers['X-XSS-Protection'] = '1; mode=block'
        # HSTS for HTTPS (only in production)
        if os.environ.get('FLASK_ENV') == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response


    # --- Blueprints (Routes) ---
    # Register your Blueprints here (Day 2 and 3 focus)
    from blueprints.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    from blueprints.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    from blueprints.champion import champion_bp
    app.register_blueprint(champion_bp, url_prefix='/champion')
    from blueprints.supervisor import supervisor_bp
    app.register_blueprint(supervisor_bp, url_prefix='/supervisor')
    
    # API Blueprints
    from blueprints.events import events_bp
    app.register_blueprint(events_bp)
    from blueprints.blog import blog_bp
    app.register_blueprint(blog_bp)
    from blueprints.public_auth import public_auth_bp
    app.register_blueprint(public_auth_bp)
    from blueprints.api import api_bp
    app.register_blueprint(api_bp)
    # Register token-only API blueprint (exempted from CSRF)
    try:
        from blueprints.api_token import api_token_bp
        app.register_blueprint(api_token_bp)
    except Exception:
        app.logger.info('api_token blueprint not available')
    
    # Mental Health Feature Blueprints
    from blueprints.assessments import assessments_bp
    app.register_blueprint(assessments_bp)
    from blueprints.affirmations import affirmations_bp
    app.register_blueprint(affirmations_bp)
    from blueprints.participation import participation_bp
    app.register_blueprint(participation_bp)
    from blueprints.symbolic_items import symbolic_items_bp
    app.register_blueprint(symbolic_items_bp)
    
    # M-Pesa Payment Integration
    from blueprints.mpesa import mpesa_bp
    app.register_blueprint(mpesa_bp)
    
    # Defensive: ensure the specific JSON API login endpoint is exempted from CSRF
    # protection. In some deployment setups the blueprint-level exemption may be
    # missed due to import/register ordering or proxy rewrites, so explicitly
    # exempt the view function if present.
    try:
        login_view = app.view_functions.get('public_auth.api_login')
        if login_view:
            csrf.exempt(login_view)
            app.logger.info('CSRF exempted for public_auth.api_login')
    except Exception:
        app.logger.exception('Failed to explicitly exempt public_auth.api_login from CSRF')

    # Also explicitly exempt the API refresh and API login endpoints which are
    # called from single-page applications using refresh cookies. These POST
    # endpoints are intended to use the `refresh_token` cookie for auth and
    # should not be blocked by CSRF checks for API clients.
    try:
        api_refresh = app.view_functions.get('api.api_auth_refresh')
        if api_refresh:
            csrf.exempt(api_refresh)
            app.logger.info('CSRF exempted for api.api_auth_refresh')
    except Exception:
        app.logger.exception('Failed to explicitly exempt api.api_auth_refresh from CSRF')

    try:
        api_login = app.view_functions.get('api.api_auth_login')
        if api_login:
            csrf.exempt(api_login)
            app.logger.info('CSRF exempted for api.api_auth_login')
    except Exception:
        app.logger.exception('Failed to explicitly exempt api.api_auth_login from CSRF')
    
    # Podcast Management
    from blueprints.podcasts import podcasts_bp
    app.register_blueprint(podcasts_bp)
    
    # Seed Funding Applications
    from blueprints.seed_funding import seed_funding_bp
    app.register_blueprint(seed_funding_bp)
    
    # API Status & Health Checks
    from blueprints.api_status import api_status_bp
    app.register_blueprint(api_status_bp)
    # Admin debug endpoints for post-deploy verification
    try:
        from blueprints.debug import debug_bp
        app.register_blueprint(debug_bp)
    except Exception:
        app.logger.info('debug blueprint not available; skipping')
    
    # Developer Routes (Hidden - requires secret key)
    from blueprints.dev import dev
    app.register_blueprint(dev)
    
    # Exempt certain public blueprints from CSRF protection
    csrf.exempt(public_auth_bp)
    csrf.exempt(podcasts_bp)
    csrf.exempt(events_bp)
    csrf.exempt(participation_bp)
    # Instead of exempting the whole API blueprint (broad and unsafe), only
    # exempt specific token-only view functions that must accept bearer-token
    # JSON POSTs from non-browser clients (e.g. /api/checkin).
    try:
        # Exempt the token-only blueprint from CSRF protection so machine clients
        # can POST JSON without CSRF tokens. Only the token blueprint is exempt.
        from blueprints.api_token import api_token_bp as _api_token_bp
        csrf.exempt(_api_token_bp)
        app.logger.info('CSRF exempted for api_token blueprint')
    except Exception:
        # Non-fatal if blueprint isn't present (e.g., during partial deploy)
        app.logger.info('api_token blueprint not found; skipping CSRF exemption')
    csrf.exempt(seed_funding_bp)
    csrf.exempt(api_status_bp)

    # Defensive: if the specific API checkin view functions exist as endpoints,
    # ensure they're exempted from CSRF so bearer-token or machine clients
    # posting JSON are not rejected by CSRFProtect with a redirect/400.
    try:
        submit_view = app.view_functions.get('api.submit_checkin')
        if submit_view:
            csrf.exempt(submit_view)
            app.logger.info('CSRF exempted for endpoint api.submit_checkin')
    except Exception:
        app.logger.exception('Failed to exempt api.submit_checkin')

    try:
        token_submit = app.view_functions.get('api_token.token_submit_checkin')
        if token_submit:
            csrf.exempt(token_submit)
            app.logger.info('CSRF exempted for endpoint api_token.token_submit_checkin')
    except Exception:
        app.logger.exception('Failed to exempt api_token.token_submit_checkin')

    # Conditionally exempt the API blueprint from CSRF in non-production when an API token is configured
    api_token = os.environ.get('API_SMOKE_TOKEN')
    if api_token and os.environ.get('FLASK_ENV') != 'production':
        try:
            from blueprints.api import api_bp
            csrf.exempt(api_bp)
            app.logger.info('API blueprint exempted from CSRF for local token-based testing')
        except Exception:
            pass

    # Developer routes
    csrf.exempt(dev)

    # Optional: initialize Flask-Caching if available (Redis backend)
    try:
        from flask_caching import Cache
        cache = Cache(config={
            'CACHE_TYPE': 'RedisCache',
            'CACHE_REDIS_URL': os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        })
        cache.init_app(app)
        app.extensions['cache'] = cache
    except Exception:
        # Caching is optional; continue if not installed/configured
        pass

    #Main Blueprint (For simple index/redirects)
    from flask import Blueprint, render_template
    from flask_login import  current_user,login_required

    main_bp = Blueprint('main', __name__)

    @main_bp.route('/')
    def index():
        if current_user.is_authenticated:
            # Redirect directly to role-specific dashboard (case-insensitive)
            role_lower = (current_user.role or '').lower()
            if role_lower == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif role_lower == 'supervisor':
                return redirect(url_for('supervisor.dashboard'))
            elif role_lower in ['champion', 'prevention advocate']:
                if os.environ.get('USE_MEMBER_PORTAL_FOR_ADVOCATES', 'False') == 'True':
                    return redirect(os.environ.get('MEMBER_PORTAL_URL', '/member-portal'))
                return redirect(url_for('champion.dashboard'))
            else:
                # Unknown role - logout and redirect to login
                from flask_login import logout_user
                logout_user()
                flash('Your account has an invalid role. Please contact an administrator.', 'danger')
                return redirect(url_for('auth.login'))
        else:
            return redirect(url_for('auth.login'))
    
    @main_bp.route('/health')
    def health_check():
        """
        Health check endpoint for monitoring system status.
        Returns JSON with database connectivity, app status, and system info.
        """
        from flask import jsonify
        from datetime import datetime, timezone
        import time
        
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'service': 'UNDA Youth Network',
            'version': '1.0.0',
            'checks': {}
        }
        
        # Check database connection
        db_healthy = False
        db_response_time = None
        try:
            start_time = time.time()
            # Simple query to verify database is responsive
            db.session.execute(db.text('SELECT 1'))
            db_response_time = round((time.time() - start_time) * 1000, 2)  # Convert to ms
            db_healthy = True
            health_status['checks']['database'] = {
                'status': 'healthy',
                'response_time_ms': db_response_time,
                'message': 'Database connection successful'
            }
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['checks']['database'] = {
                'status': 'unhealthy',
                'error': str(e),
                'message': 'Database connection failed'
            }
        
        # Check database tables exist
        try:
            from models import User, Champion, YouthSupport
            user_count = db.session.query(User).count()
            champion_count = db.session.query(Champion).count()
            support_count = db.session.query(YouthSupport).count()
            
            health_status['checks']['database_tables'] = {
                'status': 'healthy',
                'users': user_count,
                'champions': champion_count,
                'reports': support_count,
                'message': 'All tables accessible'
            }
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['checks']['database_tables'] = {
                'status': 'unhealthy',
                'error': str(e),
                'message': 'Failed to query database tables'
            }
        
        # Check Redis connection (for rate limiting)
        redis_healthy = False
        try:
            redis_url = os.environ.get('REDIS_URL')
            if redis_url:
                # Try to ping Redis
                health_status['checks']['redis'] = {
                    'status': 'configured',
                    'message': 'Redis configured for rate limiting'
                }
            else:
                health_status['checks']['redis'] = {
                    'status': 'not_configured',
                    'message': 'Redis not configured'
                }
        except Exception as e:
            health_status['checks']['redis'] = {
                'status': 'warning',
                'error': str(e)
            }
        
        # Check Sentry integration
        sentry_dsn = os.environ.get('SENTRY_DSN')
        health_status['checks']['sentry'] = {
            'status': 'enabled' if sentry_dsn else 'disabled',
            'message': 'Error monitoring active' if sentry_dsn else 'Error monitoring not configured'
        }
        
        # Overall health determination
        http_status = 200 if health_status['status'] == 'healthy' else 503
        
        return jsonify(health_status), http_status
    
    app.register_blueprint(main_bp)    

    # --- Database Setup/Migration ---
    # Initialize Flask-Migrate for database migrations
    migrate = Migrate(app, db)

    return app, limiter


# Provide a Flask CLI-compatible factory that returns only the Flask `app` instance.
# Many tests/scripts expect `create_app()` to return `(app, limiter)`, but the
# Flask CLI expects a callable that returns a `Flask` instance (or an instance
# directly). We expose `app` as a factory that calls `create_app()` and returns
# just the Flask application to remain backward-compatible.
def flask_app_factory():
    app, _ = create_app()
    return app

# Expose `app` as the Flask CLI entrypoint (it is a factory callable).
# For production WSGI servers that import `app:app`, expose the actual
# Flask application instance (not the factory) so the server receives a
# WSGI callable. This calls the factory at import time which is acceptable
# in production; tests can continue to call `create_app()` directly.
try:
    app = flask_app_factory()
except Exception:
    # Fall back to exposing the factory callable if initialization fails
    # (keeps behavior stable for test environments or incomplete config).
    app = flask_app_factory

if __name__ == '__main__':
    _app, limiter = create_app()
    _app.run(debug=True)
# Note: Do not call create_app() at import time to avoid initializing
# networked integrations (Sentry, external services) during test collection.
# Flask CLI can use the factory via `FLASK_APP="app:create_app"`.
