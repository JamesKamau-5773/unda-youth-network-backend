from models import db, User, Champion
import os
from flask import Flask, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

load_dotenv()

# Import models to ensure they are registered with SQLAlchemy


def create_app():
    app = Flask(__name__)

    # --- Configuration ---
    app.config['SECRET_KEY'] = os.environ.get(
        'SECRET_KEY', 'default_secret_key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 'postgresql://user:password@localhost/unda_db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
    app.config['RATELIMIT_STORAGE_URL'] = os.environ.get(
        'REDIS_URL', 'redis://localhost:6379')
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"]
    )

    # --- Blueprints (Routes) ---
    # Register your Blueprints here (Day 2 and 3 focus)
    from auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    #Main Blueprint (For simple index/redirects)
    from flask import blueprint, render_template
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
    with app.app_context():
        # This creates tables based on models.py if they don't exist
        # For production, use a dedicated migration tool like Flask-Migrate/Alembic
        db.create_all()
        print("Database tables created successfully.")

    return app, limiter


if __name__ == '__main__':
    app, limiter = create_app()
    app.run(debug=True)
