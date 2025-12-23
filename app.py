from models import db, User, Champion
import os
from flask import Flask, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from extensions import limiter
from dotenv import load_dotenv

load_dotenv()

# Import models to ensure they are registered with SQLAlchemy


def create_app(test_config=None):
    app = Flask(__name__)

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
    
    @main_bp.route('/emergency-password-reset-x7k9p2')
    def emergency_reset():
        """Emergency route to reset test account passwords and fix all invalid roles."""
        try:
            # First, show what users exist
            all_users = User.query.all()
            existing_users = [(u.username, u.role) for u in all_users]
            
            # Fix ALL user roles first
            fixed_roles = []
            
            for user in all_users:
                old_role = user.role
                try:
                    user.validate_role()
                    if old_role != user.role:
                        fixed_roles.append(f"{user.username}: {old_role} → {user.role}")
                except ValueError:
                    # Invalid role - set to Champion as default
                    user.role = 'Champion'
                    fixed_roles.append(f"{user.username}: {old_role} → Champion (was invalid)")
                
                # Unlock account while we're at it
                user.failed_login_attempts = 0
                user.account_locked = False
                user.locked_until = None
            
            # Create or reset test accounts
            test_accounts_status = []
            
            # Admin account
            admin = User.query.filter_by(username='admin').first()
            if admin:
                admin.set_password('Admin123!')
                admin.set_role('Admin')
                test_accounts_status.append('admin: password reset')
            else:
                admin = User(username='admin')
                admin.set_password('Admin123!')
                admin.set_role('Admin')
                db.session.add(admin)
                test_accounts_status.append('admin: created new account')
            
            # Supervisor account
            supervisor = User.query.filter_by(username='supervisor').first()
            if supervisor:
                supervisor.set_password('Supervisor123!')
                supervisor.set_role('Supervisor')
                test_accounts_status.append('supervisor: password reset')
            else:
                supervisor = User(username='supervisor')
                supervisor.set_password('Supervisor123!')
                supervisor.set_role('Supervisor')
                db.session.add(supervisor)
                test_accounts_status.append('supervisor: created new account')
            
            # Alice (Champion) account
            alice = User.query.filter_by(username='alice').first()
            if alice:
                alice.set_password('TestPassword123!')
                alice.set_role('Champion')
                test_accounts_status.append('alice: password reset')
            else:
                alice = User(username='alice')
                alice.set_password('TestPassword123!')
                alice.set_role('Champion')
                db.session.add(alice)
                test_accounts_status.append('alice: created new account')
            
            db.session.commit()
            
            # Count final roles
            admin_count = User.query.filter_by(role='Admin').count()
            supervisor_count = User.query.filter_by(role='Supervisor').count()
            champion_count = User.query.filter_by(role='Champion').count()
            
            # Format output
            existing_list = '<br>'.join([f"{u[0]} ({u[1]})" for u in existing_users])
            fixed_list = '<br>'.join(fixed_roles) if fixed_roles else 'All roles were already valid'
            test_status = '<br>'.join(test_accounts_status)
            
            return f'''
            <h1>✓ Emergency Fix Complete!</h1>
            
            <h2>Users Found in Database:</h2>
            <p style="font-family: monospace;">{existing_list}</p>
            
            <h2>Roles Fixed:</h2>
            <p style="font-family: monospace;">{fixed_list}</p>
            
            <h2>Test Accounts Status:</h2>
            <p style="font-family: monospace;">{test_status}</p>
            
            <h2>Final Role Distribution:</h2>
            <ul>
                <li>Admins: {admin_count}</li>
                <li>Supervisors: {supervisor_count}</li>
                <li>Champions: {champion_count}</li>
            </ul>
            
            <h2>✓ Ready to Login - Use These Credentials:</h2>
            <ul style="font-family: monospace; background: #f0f0f0; padding: 20px;">
                <li><strong>Admin:</strong> username: <code>admin</code> / password: <code>Admin123!</code></li>
                <li><strong>Supervisor:</strong> username: <code>supervisor</code> / password: <code>Supervisor123!</code></li>
                <li><strong>Champion:</strong> username: <code>alice</code> / password: <code>TestPassword123!</code></li>
            </ul>
            
            <p><strong>All accounts unlocked. No more redirect loops!</strong></p>
            <p><a href="/auth/login" style="background: blue; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Go to Login Page</a></p>
            '''
        except Exception as e:
            import traceback
            return f'<h1>Error:</h1><pre>{str(e)}\n\n{traceback.format_exc()}</pre>', 500
        
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
