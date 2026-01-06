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

      # Role check (case-insensitive to avoid mismatches)
      user_role = (current_user.role or '').strip()
      allowed = [r.strip() for r in roles]
      
      # Handle legacy 'Champion' role mapping
      if user_role.lower() == 'champion':
        user_role = 'Prevention Advocate'
      
      if user_role.lower() not in [r.lower() for r in allowed]:
        flash('Access denied. You do not have the required permissions.', 'danger')
        # Redirect to user's appropriate dashboard instead of main.index
        if user_role.lower() == 'admin':
          return redirect(url_for('admin.dashboard'))
        elif user_role.lower() == 'supervisor':
          return redirect(url_for('supervisor.dashboard'))
        elif user_role.lower() in ['prevention advocate', 'champion']:
          return redirect(url_for('champion.dashboard'))  # Keep existing route for now
        else:
          return redirect(url_for('auth.login'))
      return f(*args, **kwargs)
    return decorated_function
  return wrapper

#Convenience Decorators for clarity
# Use canonical role strings; decorator is case-insensitive
admin_required = roles_required('Admin')
supervisor_required = roles_required('Admin', 'Supervisor')

# New UMV Prevention Program role
prevention_advocate_required = roles_required('Admin', 'Supervisor', 'Prevention Advocate')

# Legacy decorator - maps to Prevention Advocate for backward compatibility
champion_required = roles_required('Admin', 'Supervisor', 'Prevention Advocate', 'Champion')
