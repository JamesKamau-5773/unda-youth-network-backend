How to load the idempotency alerting rules into Prometheus

1) Copy the rule file into your Prometheus `rules` directory and add it to `prometheus.yml`:

Example `prometheus.yml` snippet:

rule_files:
  - 'rules/idempotency_alerts.yml'

# Or point to a folder containing .yml files
rule_files:
  - 'rules/*.yml'

2) If running Prometheus in Docker, mount the repo `monitoring/prometheus` directory into the container and point `prometheus.yml` at the `rules/` path inside the container.

3) Reload Prometheus configuration (SIGHUP or HTTP reload endpoint):

```bash
# If Prometheus supports HTTP reload
curl -X POST http://<prometheus-host>:9090/-/reload

# Or restart the container/service
docker restart prometheus
# or
systemctl restart prometheus
```

4) Verify the rules are loaded:

- Visit the Prometheus UI -> "Alerts" to see `HighIdempotencyDuplicateRate` and `IdempotencyDuplicatesSpike`.
- Query the metrics (`idempotency_duplicate_total`, `idempotency_success_total`) in Prometheus "Graph" to confirm data flow.

Notes
- The alert thresholds in `monitoring/prometheus/idempotency_alerts.yml` are examples. Tune them to your production traffic characteristics.
- Ensure your Prometheus scrape job is configured to scrape your Flask application's `/metrics` endpoint.
