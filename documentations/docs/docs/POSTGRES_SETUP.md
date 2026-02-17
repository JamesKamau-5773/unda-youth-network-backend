## Local PostgreSQL setup for development

This project supports PostgreSQL via the `DATABASE_URL` environment variable.
By default the app will refuse to start unless `DATABASE_URL` is set (unless
you enable `FALLBACK_TO_SQLITE=true`). To run the app locally with Postgres:

1. Install Postgres locally (macOS/homebrew, apt on Ubuntu, etc.).

2. Create a database and user for development. Example commands:

```
sudo -u postgres psql -c "CREATE USER unda_user WITH PASSWORD 'unda_pass';"
sudo -u postgres psql -c "CREATE DATABASE unda_dev OWNER unda_user;"
```

3. Set `DATABASE_URL` in your `.env` or environment. Example `.env` entry:

```
DATABASE_URL=postgresql://unda_user:unda_pass@localhost:5432/unda_dev
```

4. Install Python requirements (includes `psycopg2-binary`):

```bash
python3 -m pip install -r requirements.txt
```

5. Run database migrations (Flask-Migrate / Alembic):

```bash
export FLASK_APP=app.py
flask db upgrade
```

6. (Optional) Create an admin account for testing using environment bootstrapping:

```bash
export ADMIN_TEMP_PASSWORD=your_test_password
export ADMIN_TEMP_USERNAME=test_admin
flask run
# The app startup will create/reset the admin user if the variables are set
```

Notes
- `app.py` will rewrite `postgres://` URIs to `postgresql://` when necessary.
- If you prefer to keep SQLite for some environments, set `FALLBACK_TO_SQLITE=true`.
