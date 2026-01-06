from .admin import admin_bp
from .auth import auth_bp
from .main import main_bp
from .champion import champion_bp
from .supervisor import supervisor_bp
from .podcasts import podcasts_bp
from .blog import blog_bp
from .affirmations import affirmations_bp
from .symbolic_items import symbolic_items_bp
from .events import events_bp
from .participation import participation_bp
from .seed_funding import seed_funding_bp
from .assessments import assessments_bp
from .mpesa import mpesa_bp
from .api import api_bp
from .public_auth import public_auth_bp
from .api_status import api_status_bp

def register_blueprints(app):
    """Register all blueprints with the Flask app."""
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(champion_bp, url_prefix='/champion')
    app.register_blueprint(supervisor_bp, url_prefix='/supervisor')
    app.register_blueprint(podcasts_bp, url_prefix='/podcasts')
    app.register_blueprint(blog_bp, url_prefix='/blog')
    app.register_blueprint(affirmations_bp, url_prefix='/affirmations')
    app.register_blueprint(symbolic_items_bp, url_prefix='/symbolic-items')
    app.register_blueprint(events_bp, url_prefix='/events')
    app.register_blueprint(participation_bp, url_prefix='/participation')
    app.register_blueprint(seed_funding_bp, url_prefix='/seed-funding')
    app.register_blueprint(assessments_bp)
    app.register_blueprint(mpesa_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(public_auth_bp)
    app.register_blueprint(api_status_bp)
