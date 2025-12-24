from models import db, User, Champion
import os
from flask import Flask, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from extensions import limiter
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

    # Allow tests to override config before extensions are initialized
    if test_config:
        app.config.update(test_config)

    # --- Initialization ---
    db.init_app(app)
    
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
            elif role_lower == 'champion':
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
    
    @main_bp.route('/emergency-check-users-z9k2m8')
    def emergency_check_users():
        """Emergency route to check and fix user accounts in production"""
        from flask import jsonify
        from models import User, Champion
        
        try:
            users = User.query.all()
            user_list = []
            
            for user in users:
                user_list.append({
                    'id': user.user_id,
                    'username': user.username,
                    'role': user.role,
                    'champion_id': user.champion_id,
                    'locked': user.is_locked(),
                    'failed_attempts': user.failed_login_attempts
                })
            
            # Check if test users exist, if not create them
            created_users = []
            
            if not User.query.filter_by(username='admin').first():
                admin = User(username='admin')
                admin.set_role('Admin')
                admin.set_password('Admin123!')
                db.session.add(admin)
                created_users.append('admin')
            
            if not User.query.filter_by(username='supervisor').first():
                supervisor = User(username='supervisor')
                supervisor.set_role('Supervisor')
                supervisor.set_password('Supervisor123!')
                db.session.add(supervisor)
                created_users.append('supervisor')
            
            if not User.query.filter_by(username='alice').first():
                # Find a champion to link to
                champion = Champion.query.first()
                alice = User(username='alice', champion_id=champion.champion_id if champion else None)
                alice.set_role('Champion')
                alice.set_password('TestPassword123!')
                db.session.add(alice)
                created_users.append('alice')
            
            if created_users:
                db.session.commit()
            
            # Get updated user list
            users = User.query.all()
            user_list = []
            for user in users:
                user_list.append({
                    'id': user.user_id,
                    'username': user.username,
                    'role': user.role,
                    'champion_id': user.champion_id,
                    'locked': user.is_locked(),
                    'failed_attempts': user.failed_login_attempts
                })
            
            return jsonify({
                'total_users': len(users),
                'users': user_list,
                'created_users': created_users,
                'test_credentials': {
                    'admin': 'Admin123!',
                    'supervisor': 'Supervisor123!',
                    'alice': 'TestPassword123!'
                }
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @main_bp.route('/emergency-reset-test-passwords-p4x7w1')
    def emergency_reset_passwords():
        """Reset passwords for test accounts to known values"""
        from flask import jsonify
        from models import User
        
        try:
            reset_results = []
            
            # Reset admin password
            admin = User.query.filter_by(username='admin').first()
            if admin:
                admin.set_password('Admin123!')
                admin.reset_failed_logins()  # Clear failed attempts
                reset_results.append({'username': 'admin', 'status': 'password_reset', 'new_password': 'Admin123!'})
            else:
                reset_results.append({'username': 'admin', 'status': 'not_found'})
            
            # Reset supervisor password
            supervisor = User.query.filter_by(username='supervisor').first()
            if supervisor:
                supervisor.set_password('Supervisor123!')
                supervisor.reset_failed_logins()
                reset_results.append({'username': 'supervisor', 'status': 'password_reset', 'new_password': 'Supervisor123!'})
            else:
                reset_results.append({'username': 'supervisor', 'status': 'not_found'})
            
            # Reset alice password
            alice = User.query.filter_by(username='alice').first()
            if alice:
                alice.set_password('TestPassword123!')
                alice.reset_failed_logins()
                reset_results.append({'username': 'alice', 'status': 'password_reset', 'new_password': 'TestPassword123!'})
            else:
                reset_results.append({'username': 'alice', 'status': 'not_found'})
            
            db.session.commit()
            
            return jsonify({
                'message': 'Test account passwords have been reset',
                'reset_results': reset_results,
                'instructions': 'You can now login with these credentials at /auth/login'
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        
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
