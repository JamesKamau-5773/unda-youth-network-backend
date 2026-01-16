Local Redis and app run instructions

1) Start Redis via Docker Compose (recommended when Docker is available):

```bash
# from project root
docker compose -f docker-compose.redis.yml up -d
# verify
docker compose -f docker-compose.redis.yml logs -f
redis-cli ping # should reply PONG (if installed locally)
```

2) Start the app locally (use SQLite dev DB and mock M-Pesa to avoid external calls):

```bash
export REDIS_URL='redis://localhost:6379/0'
export SQLALCHEMY_DATABASE_URI='sqlite:///dev.db'
export FLASK_ENV=development
export MPESA_MOCK=true
python app.py
```

3) Smoke test the STK endpoint with a curl POST (example):

```bash
curl -v -X POST http://127.0.0.1:5000/api/mpesa/checkout \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: idem-123" \
  -d '{"phoneNumber":"254712345678","amount":100}'
```

Repeat the same command — the second request should return the stored response or indicate processing.

Notes:
- If you cannot use Docker, install `redis-server` via your OS package manager (e.g., `sudo apt install redis-server`).
- This document only exercises local development flows. For staging/production, ensure you have an authenticated M-Pesa sandbox account and proper env vars.
