````markdown
Benchmarks
==========

Quick start:

1. Start the app locally (development):

```bash
export FLASK_APP="app:create_app"
export FLASK_ENV=development
python3 app.py
```

2. Run the simple load tester:

```bash
python3 benchmarks/load_test.py http://127.0.0.1:5000/ 100 10
```

For more realistic load testing, use `wrk`, `locust`, or cloud-based load tools.

````