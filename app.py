from models import db, User, Champion
import os
from flask import Flask, redirect, url_for, flash, request, jsonify
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

# Initialize Sentry for error tracking (production only)
sentry_dsn = os.environ.get('SENTRY_DSN')
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[FlaskIntegration()],
        traces_sample_rate=1.0,  # Capture 100% of transactions for performance monitoring
        profiles_sample_rate=1.0,  # Capture 100% of profiles
        environment=os.environ.get('FLASK_ENV', 'production'),
    )

# Import models to ensure they are registered with SQLAlchemy


def create_app(test_config=None):
    app = Flask(__name__)
    
    # Initialize Prometheus metrics
    metrics = PrometheusMetrics(app)
    
    # Track additional custom metrics
    metrics.info('app_info', 'UNDA Youth Network Application', version='1.0.0')

    # --- Configuration ---
    # SECRET_KEY is required - no fallback for production
    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        raise ValueError("SECRET_KEY environment variable must be set")
    app.config['SECRET_KEY'] = secret_key
    
    # Database URI from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable must be set")
    
    # Fix for Render/Heroku: they use postgres:// but SQLAlchemy 1.4+ requires postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Database connection pool settings
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,  # Verify connections before using
        'connect_args': {
            'connect_timeout': 10,  # 10 second connection timeout
            'options': '-c statement_timeout=30000'  # 30 second query timeout
        }
    }
    
    # Rate limiting storage
    app.config.setdefault('RATELIMIT_STORAGE_URL', os.environ.get(
        'REDIS_URL', 'redis://localhost:6379'))
    
    # Session security settings
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
    
    # WTF-CSRF Protection
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
    
    # Validate email configuration on startup
    email_config_warnings = []
    if not app.config.get('MAIL_USERNAME'):
        email_config_warnings.append('MAIL_USERNAME not set - email sending will fail')
    if not app.config.get('MAIL_PASSWORD'):
        email_config_warnings.append('MAIL_PASSWORD not set - email sending will fail')
    if not app.config.get('MAIL_DEFAULT_SENDER'):
        email_config_warnings.append('MAIL_DEFAULT_SENDER not set - using fallback')
    
    if email_config_warnings:
        print("\n⚠️  EMAIL CONFIGURATION WARNINGS:")
        for warning in email_config_warnings:
            print(f"   - {warning}")
        print("   → Set these in your .env file to enable email notifications\n")

    # Allow tests to override config before extensions are initialized
    if test_config:
        app.config.update(test_config)

    # --- Initialization ---
    db.init_app(app)
    
    # Initialize Flask-Mail
    init_mail(app)
    
    # CORS Configuration - Allow API access from different origins
    cors_origins = os.environ.get('CORS_ORIGINS', '*')  # Allow all origins for now
    
    # Custom origin validation for Netlify preview URLs
    def is_valid_origin(origin):
        if cors_origins == '*':
            return True
        allowed = cors_origins.split(',')
        # Allow any Netlify subdomain
        if origin and ('netlify.app' in origin or 'localhost' in origin):
            return True
        return origin in allowed
    
    # Enable CORS for API and auth endpoints (and other public routes).
    # Use a broad resource pattern so preflight requests for `/auth/*`
    # and other non-`/api/*` endpoints also receive CORS headers.
    CORS(app, resources={
        r"/*": {
            "origins": is_valid_origin if cors_origins != '*' else '*',
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Type"],
            "supports_credentials": True,
            "max_age": 3600
        }
    })
    
    # CSRF Protection
    csrf = CSRFProtect(app)
    
    # CSRF error handler
    @app.errorhandler(400)
    def handle_csrf_error(e):
        error_msg = str(e)
        if 'CSRF' in error_msg or 'csrf' in error_msg.lower():
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
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        """Handle 429 Too Many Requests (rate limit exceeded)"""
        if request.is_json or request.path.startswith('/api/'):
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
        
        if request.is_json or request.path.startswith('/api/'):
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
        # Prevent redirect loops - directly redirect to login without using url_for in request context
        return redirect('/auth/login')

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
    from blueprints.api import api_bp
    app.register_blueprint(api_bp)
    
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
    
    # Public Authentication & Applications
    from blueprints.public_auth import public_auth_bp
    app.register_blueprint(public_auth_bp)
    
    # Podcast Management
    from blueprints.podcasts import podcasts_bp
    app.register_blueprint(podcasts_bp)
    
    # Seed Funding Applications
    from blueprints.seed_funding import seed_funding_bp
    app.register_blueprint(seed_funding_bp)
    
    # API Status & Health Checks
    from blueprints.api_status import api_status_bp
    app.register_blueprint(api_status_bp)
    
    # Developer Routes (Hidden - requires secret key)
    from blueprints.dev import dev
    app.register_blueprint(dev)
    
    # Exempt API routes from CSRF protection
    csrf.exempt(public_auth_bp)
    csrf.exempt(podcasts_bp)
    csrf.exempt(events_bp)
    csrf.exempt(participation_bp)
    csrf.exempt(seed_funding_bp)
    csrf.exempt(api_status_bp)
    csrf.exempt(dev)

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
        from datetime import datetime
        import time
        
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
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


if __name__ == '__main__':
    app, limiter = create_app()
    app.run(debug=True)
else:
    # For Flask CLI commands (flask db init, etc.)
    app, _ = create_app()
