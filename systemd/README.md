Systemd unit files for running the UNDA application services (development / production helper).

Files added
- `systemd/gunicorn.service` — systemd unit to run Gunicorn binding `wsgi:app`.
- `systemd/celery.service` — systemd unit to run a Celery worker using `celery_worker.celery`.

Setup
1. Create a small env file with production values (optional):

```ini
# /etc/unda/unda.env
REDIS_URL=redis://127.0.0.1:6379/0
DATABASE_URL=postgresql://user:pass@db:5432/unda
SECRET_KEY=your-secret
# Any other envs your app requires
```

2. Copy unit files to systemd and reload:

```bash
sudo cp systemd/gunicorn.service /etc/systemd/system/gunicorn.service
sudo cp systemd/celery.service /etc/systemd/system/celery.service
sudo mkdir -p /etc/unda
sudo chown $USER:$USER /etc/unda
sudo cp /etc/unda/unda.env /etc/unda/unda.env || true
sudo systemctl daemon-reload
```

Start and enable services

```bash
# Start and enable gunicorn
sudo systemctl enable --now gunicorn.service
sudo systemctl status gunicorn.service

# Start and enable celery
sudo systemctl enable --now celery.service
sudo systemctl status celery.service
```

Logs

Use `journalctl` to follow logs:

```bash
sudo journalctl -u gunicorn -f
sudo journalctl -u celery -f
```

Notes
- The units assume the project is located at `/home/james/projects/unda` and the virtualenv is `/home/james/projects/unda/.venv`.
- Update `User` / `Group` in the unit files to a dedicated service user for production deployment.
- You can override any environment variables by placing them in `/etc/unda/unda.env`.
