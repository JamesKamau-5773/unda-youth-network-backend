#!/usr/bin/env python3
"""Generate traffic against the local app to exercise idempotency metrics.

This script calls the developer-only endpoint `/__dev__/simulate_mpesa` which
must be protected by `DEV_SECRET_KEY` (set in environment or passed).

Usage:
  DEV_SECRET_KEY=yourkey python3 scripts/generate_traffic.py

Environment:
  TARGET_URL - base URL of the app (default http://127.0.0.1:5000)
  DEV_SECRET_KEY - required dev key (default 'your-secret-dev-key-change-this')
  COUNT - number of unique reservations (default 200)
  DUPLICATES - number of duplicate attempts (default 50)

The script will print the JSON response and also poll `/health` a few times.
"""
import os
import sys
import time
import requests

TARGET = os.environ.get('TARGET_URL', 'http://127.0.0.1:5000')
DEV_KEY = os.environ.get('DEV_SECRET_KEY', 'your-secret-dev-key-change-this')
COUNT = int(os.environ.get('COUNT', '200'))
DUPLICATES = int(os.environ.get('DUPLICATES', '50'))

SIM_ENDPOINT = f"{TARGET.rstrip('/')}/__dev__/simulate_mpesa"
HEALTH = f"{TARGET.rstrip('/')}/health"


def main():
    print(f"Simulating {COUNT} reservations + {DUPLICATES} duplicates against {SIM_ENDPOINT}")

    params = {
        'key': DEV_KEY,
        'count': COUNT,
        'duplicates': DUPLICATES,
        'sleep_ms': 2,
    }

    try:
        resp = requests.get(SIM_ENDPOINT, params=params, timeout=60)
    except Exception as e:
        print(f"Failed to call simulate endpoint: {e}")
        sys.exit(2)

    try:
        print('Simulation response:')
        print(resp.status_code, resp.json())
    except Exception:
        print('Non-JSON response:', resp.status_code, resp.text[:200])

    # Hit health endpoint a few times to generate general traffic metrics
    for i in range(5):
        try:
            r = requests.get(HEALTH, timeout=5)
            print(f"health {i}:", r.status_code)
        except Exception as e:
            print(f"health {i} failed: {e}")
        time.sleep(0.2)

    print('\nDone. Check Grafana / Prometheus dashboards for metrics updates.')


if __name__ == '__main__':
    main()
