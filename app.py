from models import db, User, Champion
import os
from flask import Flask, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from extensions import limiter
from dotenv import load_dotenv

load_dotenv()

# Import models to ensure they are registered with SQLAlchemy


def create_app(test_config=None):
    app = Flask(__name__)

    # --- Configuration ---
    app.config['SECRET_KEY'] = os.environ.get(
        'SECRET_KEY', 'default_secret_key')
    app.config.setdefault('SQLALCHEMY_DATABASE_URI', os.environ.get(
        'DATABASE_URL', 'sqlite:///unda.db'))
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config.setdefault('RATELIMIT_STORAGE_URL', os.environ.get(
        'REDIS_URL', 'redis://localhost:6379'))

    # Allow tests to override config before extensions are initialized
    if test_config:
        app.config.update(test_config)

    # --- Initialization ---
    db.init_app(app)

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


    # --- Blueprints (Routes) ---
    # Register your Blueprints here (Day 2 and 3 focus)
    from blueprints.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    from blueprints.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    from blueprints.champion import champion_bp
    app.register_blueprint(champion_bp)

    #Main Blueprint (For simple index/redirects)
    from flask import Blueprint, render_template
    from flask_login import  current_user,login_required

    main_bp = Blueprint('main', __name__)

    @main_bp.route('/')
    def index():
        return redirect(url_for('main.dashboard_redirect'))
    
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

# For Flask CLI commands (flask db init, etc.)
app, _ = create_app()
