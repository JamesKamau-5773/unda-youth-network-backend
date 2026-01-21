````markdown
# EMERGENCY: Fix Redirect Loop on Render

## Problem
The site shows "redirected you too many times" error.

## Cause
Production database has users with invalid roles (incorrect capitalization, typos, or invalid values).

## Quick Fix (Run on Render Console)

### Step 1: Access Render Shell
1. Go to your Render dashboard
2. Click on your web service (`unda-youth-network-backend`)
3. Click "Shell" tab on the left
4. Wait for shell to connect

### Step 2: Run Fix Script
Copy and paste this command into the Render shell:

```bash
python fix_production_roles.py
```

### Step 3: Verify Output
You should see:
```
====================================
PRODUCTION ROLE FIX SCRIPT
====================================

Found X total users

OK: admin - 'Admin'
FIXED: alice - 'prevention advocate' -> 'Prevention Advocate'
...

====================================
SUCCESS: Fixed X user roles
====================================

FINAL ROLE DISTRIBUTION:
Admin: X users
Supervisor: X users  
Prevention Advocate: X users

====================================
DEPLOYMENT READY - No redirect loops expected
====================================
```

### Step 4: Restart Service
After the script completes:
1. Exit the shell
2. Click "Manual Deploy" → "Clear build cache & deploy"
3. Wait for deployment to complete
4. Test the site

## Alternative: Run Via Python Console

If you have access to Python console on Render:

```python
from app import create_app
from models import db, User

app, _ = create_app()
with app.app_context():
    users = User.query.all()
    for user in users:
        try:
            user.validate_role()
        except:
            user.role = 'Prevention Advocate'
    db.session.commit()
    print("Roles fixed!")
```

## Prevention

This issue is now prevented by:
1. Role validation on user creation
2. `fix_user_roles.py` script for regular checks
3. Redirect loop breakers in auth routes

## If Problem Persists

If redirect loop continues after running the fix:

1. **Check specific user:**
   ```python
   from app import create_app
   from models import db, User
   
   app, _ = create_app()
   with app.app_context():
       # Replace 'username' with the problematic user
       user = User.query.filter_by(username='alice').first()
       print(f"Role: {user.role}")
       user.role = 'Prevention Advocate'  # or 'Admin' or 'Supervisor'
       db.session.commit()
   ```

2. **Clear browser cache and cookies**
3. **Try incognito/private browsing**
4. **Check Render logs** for error messages

## Contact

If you need help, the issue is likely one of:
- Invalid role in database (run fix script)
- Cached redirect in browser (clear cache)
- Session corruption (clear cookies)

````