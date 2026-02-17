Playwright setup and run

Install dependencies in your venv:

```bash
pip install playwright
python -m playwright install
```

Run the admin flow test script:

```bash
PYTHONPATH=/home/james/projects/unda /home/james/projects/unda/.venv/bin/python scripts/playwright_admin_flows.py
```

This test logs in as `test_admin` and runs a toolkit and UMV create+verify flow. Adjust `ADMIN_USER`/`ADMIN_PW` in the script if needed.
