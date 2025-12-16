from functools import wraps
from flask import abort, redirect, url_for,flash
from flask_login import current_user

def roles_required(*roles):
  def wrapper(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
      if not current_user.is_authenticated:
        return f(*args, **kwargs)
      
      if current_user.role not in roles:
        flash('Access denied. You do not have the required permissions.', 'danger')
        return redirect(url_for('main.index'))
      return f(*args, **kwargs)
    return decorated_function
  return wrapper

#Convenience Decorators for clarity
admin_required = roles_required('admin')
supervisor_required = roles_required('admin', 'supervisor')
champion_required = roles_required('admin', 'supervisor', 'champion')
