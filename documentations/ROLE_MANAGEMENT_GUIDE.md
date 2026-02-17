# Role Management Guide - Preventing Role Inconsistencies

## Overview
This guide ensures consistent role handling across the UMV Prevention application to prevent "invalid role" errors and access issues.

## Role Constants (Single Source of Truth)

**Location:** `models.py` - User class

```python
# Valid roles list
User.VALID_ROLES = ['Admin', 'Supervisor', 'Prevention Advocate']

# Role constants (use these in code)
User.ROLE_ADMIN = 'Admin'
User.ROLE_SUPERVISOR = 'Supervisor'
User.ROLE_PREVENTION_ADVOCATE = 'Prevention Advocate'
```

## Rules for Role Management

###  DO: Use Constants

```python
#  CORRECT - Use constants
new_user = User(username=username)
new_user.set_role(User.ROLE_PREVENTION_ADVOCATE)

#  CORRECT - Query with constants
supervisors = User.query.filter_by(role=User.ROLE_SUPERVISOR).all()

#  CORRECT - Role checks
if current_user.is_role(User.ROLE_ADMIN):
    # Admin actions
```

###  DON'T: Hard-code Strings

```python
#  WRONG - Hard-coded string (prone to typos)
new_user = User(username=username, role='Prevention Advocate')

#  WRONG - Direct assignment bypasses validation
new_user.role = 'Champion'  # Old role name

#  WRONG - Case-sensitive comparison
if user.role == 'admin':  # Won't match 'Admin'
```

## User Model Methods

### 1. `set_role(role_name)` - Safe Role Assignment
**Use this for all role assignments**

```python
# Automatically validates, capitalizes, and handles legacy names
user.set_role(User.ROLE_PREVENTION_ADVOCATE)
user.set_role('admin')  # Auto-corrects to 'Admin'
user.set_role('Champion')  # Auto-converts to 'Prevention Advocate'
```

**Raises ValueError if invalid role**

### 2. `validate_role()` - Normalize Existing Roles
**Use after database queries or migrations**

```python
user = User.query.filter_by(username='john').first()
user.validate_role()  # Fixes case and legacy names
db.session.commit()
```

### 3. `is_role(role_name)` - Safe Role Checking
**Use for comparisons (case-insensitive, handles legacy names)**

```python
if user.is_role('admin'):  # Returns True for 'Admin'
    # Admin logic

if user.is_role('Champion'):  # Returns True for 'Prevention Advocate'
    # Advocate logic
```

## Code Patterns

### Creating New Users

```python
# Pattern 1: Admin creating advocate
new_user = User(username=username, email=email)
new_user.set_role(User.ROLE_PREVENTION_ADVOCATE)
new_user.set_password(temp_password)
db.session.add(new_user)

# Pattern 2: Creating supervisor
supervisor = User(username=username)
supervisor.set_role(User.ROLE_SUPERVISOR)
supervisor.set_password(password)
db.session.add(supervisor)
```

### Querying by Role

```python
# Get all supervisors
supervisors = User.query.filter_by(role=User.ROLE_SUPERVISOR).all()

# Get all advocates (handles legacy 'Champion' in DB)
advocates = User.query.filter(
    db.or_(
        User.role == User.ROLE_PREVENTION_ADVOCATE,
        User.role == 'Champion'  # Legacy data
    )
).all()
```

### Authorization Decorators

```python
from decorators import role_required

@admin_bp.route('/users/create')
@login_required
@role_required(User.ROLE_ADMIN)  # Use constant
def create_user():
    # Only admins can access
```

### Template Rendering

```python
# Pass role constant to templates
return render_template('success.html',
    role=User.ROLE_PREVENTION_ADVOCATE,  # Not 'Prevention Advocate'
    username=username
)
```

## Migration Strategy for Legacy Data

If you have users with the old 'Champion' role in the database:

```python
# Migration script
from models import User, db

# Update all Champion roles to Prevention Advocate
champions = User.query.filter_by(role='Champion').all()
for user in champions:
    user.set_role(User.ROLE_PREVENTION_ADVOCATE)
    print(f"Updated {user.username}: Champion → Prevention Advocate")

db.session.commit()
print(f"Updated {len(champions)} users")
```

## Testing Role Consistency

### Unit Test Example

```python
def test_role_assignment():
    """Ensure roles are validated correctly."""
    user = User(username='test_user')
    
    # Test valid role
    user.set_role(User.ROLE_PREVENTION_ADVOCATE)
    assert user.role == 'Prevention Advocate'
    
    # Test legacy conversion
    user.set_role('Champion')
    assert user.role == 'Prevention Advocate'
    
    # Test case correction
    user.set_role('admin')
    assert user.role == 'Admin'
    
    # Test invalid role
    with pytest.raises(ValueError):
        user.set_role('InvalidRole')
```

## Pre-Deployment Checklist

Before deploying role-related changes:

- [ ] All role assignments use `User.set_role()` method
- [ ] All role queries use `User.ROLE_*` constants
- [ ] All role comparisons use `user.is_role()` method
- [ ] No hard-coded role strings in Python code
- [ ] Templates receive role constants, not strings
- [ ] Authorization decorators use constants
- [ ] Database migration script ready (if needed)
- [ ] Unit tests verify role validation
- [ ] Tested with mixed legacy/new role data

## Common Mistakes to Avoid

### Mistake 1: Direct Role Assignment
```python
#  WRONG
user.role = 'Prevention Advocate'

#  CORRECT
user.set_role(User.ROLE_PREVENTION_ADVOCATE)
```

### Mistake 2: Case-Sensitive Comparison
```python
#  WRONG
if user.role.lower() == 'admin':

#  CORRECT
if user.is_role(User.ROLE_ADMIN):
```

### Mistake 3: Hard-Coded Template Values
```python
#  WRONG
return render_template('page.html', role='Admin')

#  CORRECT
return render_template('page.html', role=User.ROLE_ADMIN)
```

### Mistake 4: Forgetting Legacy Names
```python
#  WRONG - Won't find old 'Champion' records
advocates = User.query.filter_by(role='Prevention Advocate').all()

#  CORRECT - Finds both
advocates = User.query.filter(
    db.or_(User.role == User.ROLE_PREVENTION_ADVOCATE, User.role == 'Champion')
).all()
```

## Quick Reference

| Task | Method | Example |
|------|--------|---------|
| Set role | `user.set_role()` | `user.set_role(User.ROLE_ADMIN)` |
| Check role | `user.is_role()` | `if user.is_role('admin'):` |
| Validate role | `user.validate_role()` | `user.validate_role()` |
| Query by role | `filter_by(role=constant)` | `User.query.filter_by(role=User.ROLE_SUPERVISOR)` |

## Support

If you encounter role-related issues:

1. Check user's actual role in database: `User.query.filter_by(username='alice').first().role`
2. Run validation: `user.validate_role()`
3. Check VALID_ROLES constant matches database values
4. Look for hard-coded role strings in code
5. Review this guide for proper patterns

---

**Last Updated:** January 2025  
**Maintainer:** UMV Prevention Development Team
