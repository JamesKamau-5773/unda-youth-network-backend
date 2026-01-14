"""WSGI entrypoint for deployment.

Exports a WSGI `app` instance as `app` so servers (Gunicorn, Render)
can load the application via `wsgi:app`.

This intentionally creates the app at import time which is appropriate for
production deployment; tests use the `create_app()` factory in `app.py`.
"""
from app import create_app

# Create the application instance using environment configuration
app, _ = create_app()
