from flask import Blueprint
from flask_login import login_required
from decorators import admin_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/settings')
@login_required
@admin_required
def settings():
    return 'Admin settings'
