from functools import wraps
from flask import abort, redirect, url_for,flash
from flask_login import current_user

def roles_required(*roles):
  def wrapper(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
      # Require authentication
      if not current_user.is_authenticated:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('auth.login'))

      # Role check (roles passed should match stored role strings)
      if current_user.role not in roles:
        flash('Access denied. You do not have the required permissions.', 'danger')
        return redirect(url_for('main.index'))
      return f(*args, **kwargs)
    return decorated_function
  return wrapper

#Convenience Decorators for clarity
# Use canonical role strings (capitalized) throughout the app
admin_required = roles_required('Admin')
supervisor_required = roles_required('Admin', 'Supervisor')
champion_required = roles_required('Admin', 'Supervisor', 'Champion')
