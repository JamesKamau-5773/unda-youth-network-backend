from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from models import db, User, Champion
from app import limiter

auth_bp = Blueprint ('auth', __name__, template_folder='templates')

# --- Helper function for password hashing/checking is in models.py ---
@auth_bp.route('/register', methods=['GET', 'POST'])
@roles_required('Admin') # Only an Admin can register new users
def register():
  if request.method == 'POST':

   #Create Champion Profile (Initial Static Data)
    champion =champion(
      full_name=request.form.get('full_name'),
      email=request.form.get('email'),
      phone_number=request.form.get('phone_number'),
      assigned_champion_code=request.form.get('assigned_champion_code'),
    )
    db.session.add(champion)
    db.session.commit()

    #Create User Login Account
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role', 'champion') # Default to Champion

    # Check for existing username/email
    if User.query.filter_by(username=username).first():
      flash('Username already exists', 'danger')
      return redirect(url_for('auth.register'))
    
    user = User(
      username=username,
      role=role,
      champion_id=champion.champion_id if role == 'champion' else None

    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()


    # Update Champion FK link if the user is a Champion
    if role == 'champion':
      champion.user_id = user.id # Assuming User ID is added to Champion
      db.session.commit()

    flash(f'New {role} account for {champion.full_name} created successfully.', 'success')  
    return redirect(url_for('main.index'))
  
  # Simple form rendering for GET request (needs an HTML template)
  return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
  if current_user.is_authenticated:
    return redirect(url_for('main.dashboard_redirect')) # Redirect if already logged in
  
  if request.method == 'POST':
    username = request.form.get('username')
    password = request.form.get('password')

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
      login_user(user, remember=True)
      flash('Login successfully!', 'success')

      # Redirect user based on their role after successful login
      return redirect(url_for('main.dashboard_redirect'))
    else:
      flash('Invalid username or password', 'danger')

  return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
  logout_user()
  flash('You have been logged out.', 'success')
  return redirect(url_for('auth.login'))