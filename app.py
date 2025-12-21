from models import db, User, Champion
import os
from flask import Flask, redirect, url_for, flash
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

    # Flask-Login setup
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # Define the login route
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Flask-Limiter setup (using Redis for persistent rate limits)
    limiter.init_app(app)
    
    # Security headers
    @app.after_request
    def set_security_headers(response):
        # Content Security Policy
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self' 'unsafe-inline';"
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
    
    # TEMPORARY: Password reset route for production (remove after use)
    from reset_passwords_route import reset_bp
    app.register_blueprint(reset_bp)

    #Main Blueprint (For simple index/redirects)
    from flask import Blueprint, render_template
    from flask_login import  current_user,login_required

    main_bp = Blueprint('main', __name__)

    @main_bp.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('main.dashboard_redirect'))
        else:
            return redirect(url_for('auth.login'))
    
    @main_bp.route('/dashboard')
    @login_required
    def dashboard_redirect():
        if current_user.role == 'Admin':
            return redirect(url_for('auth.admin_dashboard'))
        elif current_user.role == 'Supervisor':
            return redirect(url_for('auth.supervisor_dashboard'))
        else:
            return redirect(url_for('auth.champion_dashboard'))
        
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
