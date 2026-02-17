#  Production Deployment Guide

## Documentation Navigation

- [Project Overview](README.md)
- [Quick Start](QUICK_START.md)
- [Deployment Status](DEPLOYMENT_STATUS.md)
- [Security Overview](SECURITY.md)
- [Security Implementation](SECURITY_IMPLEMENTATION.md)
- [User Guide](USER_GUIDE.md)
- [Changelog](CHANGELOG.md)

This guide covers deploying the UNDA Youth Network application to production hosting providers.

---

##  Pre-Deployment Checklist

All three production requirements have been implemented:

 **Environment Variables** - `.env.example` template with all required variables  
 **Production Web Server** - `gunicorn==21.2.0` in requirements.txt  
 **Database Migrations** - All migrations verified (including 33-field prevention advocate update)

---

##  Quick Start - Local Production Test

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Create Environment File
```bash
cp .env.example .env
```

### 3. Generate Secret Key
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
Copy the output and paste into `.env` as `SECRET_KEY=<paste-here>`

### 4. Configure Database
Update `.env` with your PostgreSQL credentials:
```ini
DATABASE_URL=postgresql://your_user:your_password@localhost/unda_db
```

### 5. Apply Migrations
```bash
flask db upgrade
```

### 6. Start with Gunicorn
```bash
# Development (single worker)
gunicorn -w 1 -b 127.0.0.1:5000 app:app

# Production (4 workers)
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 app:app
```

---

##  Platform-Specific Deployment

### Railway.app (Recommended)

1. **Create New Project**
   - Go to https://railway.app
   - Click "New Project" → "Deploy from GitHub"
   - Select your repository

2. **Add PostgreSQL**
   - Click "+ New" → "Database" → "PostgreSQL"
   - Railway auto-generates `DATABASE_URL`

3. **Add Redis**
   - Click "+ New" → "Database" → "Redis"
   - Railway auto-generates `REDIS_URL`

4. **Configure Environment Variables**
   Go to your app → Variables → Raw Editor:
   ```ini
   SECRET_KEY=<generate-with-secrets-token-hex>
   FLASK_ENV=production
   ```
   (DATABASE_URL and REDIS_URL are auto-added)

5. **Configure Start Command**
   Settings → Deploy → Start Command:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:$PORT --timeout 120 app:app
   ```

6. **Deploy**
   - Railway automatically deploys on git push
   - Migrations run automatically if configured in `railway.json`

---

### Render.com

1. **Create Web Service**
   - Go to https://render.com
   - Click "New +" → "Web Service"
   - Connect GitHub repository

2. **Configure Build Settings**
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt && flask db upgrade`
   - Start Command: `gunicorn -w 4 -b 0.0.0.0:$PORT --timeout 120 app:app`

3. **Add PostgreSQL**
   - Dashboard → "New +" → "PostgreSQL"
   - Copy the "Internal Database URL"

4. **Add Redis**
   - Dashboard → "New +" → "Redis"
   - Copy the connection string

5. **Set Environment Variables**
   Web Service → Environment → Add:
   ```ini
   SECRET_KEY=<generate-with-secrets-token-hex>
   FLASK_ENV=production
   DATABASE_URL=<paste-postgres-url>
   REDIS_URL=<paste-redis-url>
   ```

6. **Deploy**
   - Render auto-deploys on git push
   - View logs for migration output

---

### Render / Gunicorn (Notes)

- For production HTTP servers prefer loading the WSGI `app` exposed by `wsgi:app`.
- Example **Start Command** (Render / Gunicorn):

```bash
# Bind to the port Render provides via `$PORT`
gunicorn -w 4 -b 0.0.0.0:$PORT --timeout 120 wsgi:app
```

- If you need to run Flask CLI commands (migrations) during build or deploy,
   set the Flask app factory wrapper as the `FLASK_APP` value. This repository
   exposes a factory callable named `app` in `app.py` which returns the
   `Flask` instance when invoked. Example:

```bash
export FLASK_APP=app:app
flask db upgrade
```

- Alternatively, prefer running migrations from a one-off runner using the
   same WSGI app context to avoid CLI factory confusion:

```bash
# Run migrations inside a one-off process
python -c "from wsgi import app; from flask_migrate import upgrade; upgrade()"
```

### Recent Render Operational Notes (Feb 2026)

- The application now includes explicit favicon handling (`/favicon.ico`) and a base template favicon link, reducing repeated favicon 404 noise in logs.
- Cookie-domain mismatch warnings are now suppressed for expected `*.onrender.com` host probes while preserving warnings for real misconfiguration on primary domains.
- If you use a custom domain (e.g. `api.undayouth.org`) with `SESSION_COOKIE_DOMAIN=.undayouth.org`, verify browser login/session behavior against the custom domain, not the Render temporary hostname.


---

### Heroku

1. **Install Heroku CLI**
   ```bash
   curl https://cli-assets.heroku.com/install.sh | sh
   heroku login
   ```

2. **Create App**
   ```bash
   heroku create your-app-name
   ```

3. **Add PostgreSQL**
   ```bash
   heroku addons:create heroku-postgresql:essential-0
   ```
   (This auto-sets `DATABASE_URL`)

4. **Add Redis**
   ```bash
   heroku addons:create heroku-redis:mini
   ```
   (This auto-sets `REDIS_URL`)

5. **Set Environment Variables**
   ```bash
   heroku config:set SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
   heroku config:set FLASK_ENV=production
   ```

6. **Create Procfile**
   ```bash
   echo "web: gunicorn -w 4 --timeout 120 app:app" > Procfile
   ```

7. **Deploy**
   ```bash
   git push heroku main
   heroku run flask db upgrade
   heroku open
   ```

---

##  Security Checklist

Before going live:

- [ ] `.env` file is in `.gitignore` (already configured)
- [ ] `SECRET_KEY` is 64+ random characters (use `secrets.token_hex(32)`)
- [ ] `FLASK_ENV=production` is set
- [ ] Database uses SSL/TLS connection
- [ ] Redis uses password authentication
- [ ] HTTPS is enabled (automatic on Railway/Render/Heroku)
- [ ] Firewall rules limit database access
- [ ] Regular database backups configured
- [ ] Error logs are monitored (Sentry, LogDNA, etc.)

---

##  Database Migrations

The application includes 3 migrations:

1. **519eca3cfb20** - Initial models (User, Prevention Advocate, Supervisor, etc.)
2. **1875158eefe9** - Account lockout security fields
3. **ca78f27269e6** - 33 comprehensive prevention advocate data fields

To apply migrations on deployment:
```bash
flask db upgrade
```

To check current migration version:
```bash
flask db current
```

---

##  Database connectivity & startup checks

The application now performs a production-only startup connectivity check to
avoid silently falling back to an ephemeral SQLite database (which would
cause data loss on redeploys).

- Ensure `DATABASE_URL` is set and points to your managed Postgres instance.
- Do NOT set `FALLBACK_TO_SQLITE=True` in non-development environments.

Behavior summary:
- In `FLASK_ENV=production` the app will run a `SELECT 1` at startup; if
   this check fails the process will abort and log the failure. This prevents
   the app from starting with an unintended SQLite database.
- If `FALLBACK_TO_SQLITE=True` is detected while not in `development`, the
   app will log a warning (and refuse to start in `production`).

If you see startup failures after deploying, check the app logs for messages
like `Database connectivity check failed at startup` and verify the
`DATABASE_URL` value in your deployment environment.


##  Gunicorn Configuration

### Basic Command
```bash
gunicorn app:app
```

### Production-Recommended
```bash
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 --access-logfile - --error-logfile - app:app
```

### Parameters Explained:
- `-w 4`: 4 worker processes (use `2 * CPU_CORES + 1`)
- `-b 0.0.0.0:5000`: Bind to all interfaces on port 5000
- `--timeout 120`: 120 second timeout for long requests
- `--access-logfile -`: Log requests to stdout
- `--error-logfile -`: Log errors to stdout
- `app:app`: Module:application (from `app.py`)

### Using gunicorn.conf.py (Advanced)
Create `gunicorn.conf.py`:
```python
import os
import multiprocessing

workers = os.getenv('WORKERS', multiprocessing.cpu_count() * 2 + 1)
bind = os.getenv('BIND', '0.0.0.0:5000')
timeout = int(os.getenv('TIMEOUT', 120))
accesslog = '-'
errorlog = '-'
loglevel = 'info'
```

Then start with:
```bash
gunicorn -c gunicorn.conf.py app:app
```

---

##  Testing Production Settings Locally

1. Set environment to production:
```bash
echo "FLASK_ENV=production" >> .env
```

2. Start with gunicorn:
```bash
gunicorn -w 2 -b 127.0.0.1:5000 app:app
```

3. Test secure cookies (should see `Secure` flag):
```bash
curl -I http://localhost:5000/login
```

4. Verify rate limiting (try 6 rapid requests):
```bash
for i in {1..6}; do curl http://localhost:5000/login; done
```

5. Check logs for errors

6. Switch back to development:
```bash
echo "FLASK_ENV=development" > .env
```

---

##  Support Resources

- **Railway Docs**: https://docs.railway.app/
- **Render Docs**: https://render.com/docs
- **Heroku Docs**: https://devcenter.heroku.com/
- **Gunicorn Docs**: https://docs.gunicorn.org/
- **Flask Deployment**: https://flask.palletsprojects.com/en/2.3.x/deploying/

---

##  Troubleshooting

### Issue: `SECRET_KEY not set`
**Solution**: Add `SECRET_KEY` to `.env` or platform environment variables

### Issue: `DATABASE_URL not set`
**Solution**: Add PostgreSQL addon and verify `DATABASE_URL` is set

### Issue: `Connection refused (Redis)`
**Solution**: Verify `REDIS_URL` is correct or Redis addon is active

### Issue: Migrations fail
**Solution**: 
```bash
flask db stamp head  # Mark current state
flask db migrate     # Generate new migration
flask db upgrade     # Apply migration
```

### Issue: Port already in use
**Solution**: 
```bash
lsof -ti:5000 | xargs kill -9  # Kill process on port 5000
```

### Issue: Workers timeout
**Solution**: Increase timeout: `gunicorn --timeout 300 app:app`

---

##  Post-Deployment

After successful deployment:

1. **Test all features**:
   - User registration/login
   - Prevention Advocate creation/editing
   - Supervisor dashboards
   - Admin panel

2. **Monitor logs** for errors:
   - Railway: Deployments → View Logs
   - Render: Logs tab
   - Heroku: `heroku logs --tail`

3. **Set up monitoring**:
   - Uptime monitoring (UptimeRobot, Pingdom)
   - Error tracking (Sentry, Rollbar)
   - Performance monitoring (New Relic, Datadog)

4. **Configure backups**:
   - Enable automatic database backups
   - Export Redis snapshots regularly

5. **Document your deployment**:
   - Note platform-specific settings
   - Document custom configuration
   - Update this guide with lessons learned

---

** Your UNDA Youth Network application is production-ready!**
