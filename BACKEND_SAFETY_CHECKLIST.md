# Backend Safety Checklist - Preventing 502 Errors

## ✅ Completed Fixes (January 2026)

### 1. **Import Threading Deadlocks** ✓
**Problem**: Importing modules inside threaded functions causes Python interpreter deadlocks.

**Solution Applied**:
- Moved `from email_utils import send_password_email` to top-level imports in `blueprints/admin.py`
- Removed all duplicate imports inside functions/threads

**Prevention Rule**: 
```python
# ❌ NEVER DO THIS
def my_thread_function():
    from some_module import some_function  # Can deadlock!
    
# ✅ ALWAYS DO THIS
from some_module import some_function  # Import at top of file

def my_thread_function():
    some_function()  # Safe to use
```

---

### 2. **Unsafe Database Lookups** ✓
**Problem**: Accessing attributes on potentially `None` database objects causes `AttributeError`.

**Solution Applied**:
- Added null checks before accessing `.username`, `.email`, etc.
- Used safe lookups with conditional blocks instead of inline ternaries

**Prevention Rule**:
```python
# ❌ NEVER DO THIS
supervisor = User.query.get(supervisor_id)
name = supervisor.username  # Crashes if supervisor is None!

# ❌ ALSO RISKY
name = User.query.get(supervisor_id).username  # Crashes if not found!

# ✅ ALWAYS DO THIS
supervisor = User.query.get(supervisor_id)
if supervisor:
    name = supervisor.username
else:
    name = "Unknown"
    
# OR use get_or_404 if the record MUST exist
supervisor = User.query.get_or_404(supervisor_id)
```

---

### 3. **Post-Commit Operations Without Error Boundaries** ✓
**Problem**: Exceptions in email sending or other post-commit operations crash the request even though the database transaction succeeded.

**Solution Applied**:
- Wrapped all email sending in try-except blocks
- Added logging for failures without breaking the response
- Ensured success page always renders even if email fails

**Prevention Rule**:
```python
# ❌ RISKY PATTERN
db.session.commit()
send_email(user.email)  # If this fails, user sees 502!
return render_template('success.html')

# ✅ SAFE PATTERN
db.session.commit()

# Post-commit operations wrapped in error boundary
try:
    send_email(user.email)
    email_sent = True
except Exception as e:
    current_app.logger.error(f"Email failed: {e}")
    email_sent = False
    # Continue anyway - main operation succeeded

return render_template('success.html', email_sent=email_sent)
```

---

### 4. **Missing Input Validation** ✓
**Problem**: Invalid foreign key values (e.g., deleted supervisor) cause constraint violations.

**Solution Applied**:
- Validate supervisor exists and has correct role before assignment
- Added proper error messages for invalid inputs

**Prevention Rule**:
```python
# ❌ ASSUME INPUT IS VALID
champion.supervisor_id = int(supervisor_id)
db.session.commit()  # May crash with FK constraint violation!

# ✅ VALIDATE BEFORE USING
supervisor = User.query.get(int(supervisor_id))
if not supervisor or supervisor.role != 'Supervisor':
    flash('Invalid supervisor selected', 'danger')
    return redirect(...)
    
champion.supervisor_id = supervisor.user_id
db.session.commit()
```

---

## 🔍 Code Review Checklist

Before deploying any route that modifies the database:

- [ ] All imports are at the top of the file (not inside functions/threads)
- [ ] Database lookups check for `None` before accessing attributes
- [ ] Post-commit operations (email, notifications) are wrapped in try-except
- [ ] Foreign key assignments validate the referenced record exists
- [ ] Success responses render even if non-critical operations fail
- [ ] Error logging is in place for debugging
- [ ] Thread functions use pre-imported modules

---

## 🚨 High-Risk Patterns to Watch For

### Pattern 1: Inline Attribute Access
```python
# Search for this pattern in code reviews:
\.query\.get\([^)]+\)\.\w+

# Examples that need fixing:
User.query.get(id).username
Champion.query.get(id).email
```

### Pattern 2: Imports Inside Functions
```python
# Search for:
def .+:\n.*from .+ import

# Red flag if found inside threaded functions
```

### Pattern 3: Bare Email Sends After Commit
```python
# Look for:
db.session.commit()
send_email(  # Should be wrapped in try-except
```

---

## 🛠️ Testing Strategy

### Manual Testing
1. **Test with invalid data**: Try to assign non-existent supervisors
2. **Test with network failures**: Disconnect from email server and create users
3. **Test with deleted records**: Delete a supervisor, then try to reassign their advocates

### Automated Testing
```python
def test_create_user_survives_email_failure(mock_email):
    """User creation should succeed even if email fails"""
    mock_email.side_effect = Exception("SMTP timeout")
    
    response = client.post('/admin/create-user', data={...})
    
    # Should still return 200 and create user
    assert response.status_code == 200
    assert User.query.filter_by(username='test').first() is not None
```

---

## 📊 Monitoring

Add alerts for:
- **Email failure rate** > 10% (indicates SMTP issues)
- **500 errors on user creation routes** (immediate investigation)
- **Database constraint violations** (data integrity issues)

---

## 📝 Updated Files

| File | Changes | Status |
|------|---------|--------|
| `blueprints/admin.py` | Fixed all 4 safety issues | ✅ Complete |
| `create_champion` route | Safe supervisor lookup, error boundaries | ✅ Complete |
| `create_user` route | Error boundary for email | ✅ Complete |
| `reset_user_password` route | Error boundary for email | ✅ Complete |
| `assign_champion` route | Safe database lookups | ✅ Complete |
| `approve_champion_application` route | Validation for user lookup | ✅ Complete |

---

## 🎯 Future Prevention

**Before merging any PR that touches user/database operations:**

1. Run: `grep -r "query.get(" blueprints/` and verify safe usage
2. Run: `grep -r "from.*import" blueprints/*.py` and check for nested imports
3. Run: `grep -r "db.session.commit" blueprints/` and verify error handling
4. Test the route with intentionally invalid data
5. Test the route with email server unreachable

---

**Last Updated**: January 8, 2026  
**Maintainer**: Development Team  
**Review Frequency**: Before each production deployment
