# Preventing Redirect Loops - Implementation Guide

## Problem
Users with invalid or unrecognized roles caused infinite redirect loops between login and dashboard routes.

## Root Causes
1. **Invalid role values in database** - Roles stored with inconsistent capitalization or typos
2. **Missing validation** - No checks when creating/updating user roles
3. **Poor error handling** - Redirecting to login when role was invalid caused infinite loops

## Solutions Implemented

### 1. Database-Level Protection

**Location:** `models.py` - User model

```python
VALID_ROLES = ['Admin', 'Supervisor', 'Prevention Advocate']
```

- Defined valid roles as a constant
- All role checks now reference this single source of truth

### 2. Role Validation Methods

**New Methods:**
- `set_role(role)` - Validates and normalizes roles before setting
- `validate_role()` - Checks and fixes existing role values

**Benefits:**
- Automatic capitalization (admin → Admin)
- Rejects invalid roles with clear error messages
- Prevents bad data from entering the database

### 3. Registration Protection

**Location:** `blueprints/auth.py` - register route

```python
try:
    user.set_role(role)
except ValueError as e:
    flash(str(e), 'danger')
    return redirect(url_for('auth.register'))
```

- Uses `set_role()` to validate before saving
- Shows user-friendly error if invalid role provided
- Prevents invalid users from being created

### 4. Redirect Loop Prevention

**Location:** `blueprints/auth.py` and `app.py`

```python
else:
    # Unknown role - logout and show error to prevent redirect loop
    logout_user()
    flash('Your account has an invalid role...', 'danger')
    return render_template('auth/login.html')
```

- Logs out users with invalid roles instead of redirecting
- Shows clear error message
- Breaks the redirect loop

### 5. Data Cleanup Script

**Location:** `fix_user_roles.py`

Run this script to:
- Scan all users for invalid roles
- Auto-fix capitalization issues
- Report any truly invalid roles
- Optionally set invalid roles to default (Prevention Advocate)

**Usage:**
```bash
python fix_user_roles.py
```

## Best Practices Going Forward

### When Creating Users
```python
user = User(username='test')
user.set_role('admin')  # Validates and normalizes to 'Admin'
user.set_password('password')
db.session.add(user)
db.session.commit()
```

### When Updating Roles
```python
try:
    user.set_role(new_role)
    db.session.commit()
except ValueError as e:
    flash(f'Invalid role: {e}', 'danger')
```

### Checking Roles
```python
# Case-insensitive check
role_lower = (current_user.role or '').lower()
if role_lower == 'admin':
    # ...
```

## Monitoring & Maintenance

### Regular Checks
1. **Run validation script monthly:**
   ```bash
   python fix_user_roles.py
   ```

2. **Check for invalid roles in production:**
   ```sql
   SELECT username, role 
   FROM users 
   WHERE role NOT IN ('Admin', 'Supervisor', 'Prevention Advocate');
   ```

3. **Monitor error logs** for role-related issues

### Database Migration (Optional)
To add a CHECK constraint at database level:

```sql
ALTER TABLE users 
ADD CONSTRAINT valid_role_check 
CHECK (role IN ('Admin', 'Supervisor', 'Prevention Advocate'));
```

## Testing Checklist

- [ ] Create user with valid role (Admin/Supervisor/Prevention Advocate)
- [ ] Try creating user with invalid role (should fail gracefully)
- [ ] Try creating user with lowercase role (should auto-capitalize)
- [ ] Login with valid role user (should route to correct dashboard)
- [ ] Access site root `/` with valid role (should redirect correctly)
- [ ] Run `fix_user_roles.py` on test database
- [ ] Verify no redirect loops occur in any scenario

## Emergency Response

If redirect loop occurs in production:

1. **Immediate fix:**
   ```python
   # Run in production console
   from app import create_app
   from models import db, User
   
   app, _ = create_app()
   with app.app_context():
       # Find problematic user
       user = User.query.filter_by(username='problematic_user').first()
       user.role = 'Prevention Advocate'  # or appropriate role
       db.session.commit()
   ```

2. **Long-term:** Run `fix_user_roles.py` to check all users

## Summary

**Multiple layers of protection:**
1.  Valid roles defined in one place
2.  Validation on user creation
3.  Validation on role updates
4.  Redirect loop breaker in routes
5.  Cleanup script for existing data
6.  Clear error messages for users

**Result:** Invalid roles cannot cause redirect loops anymore.
