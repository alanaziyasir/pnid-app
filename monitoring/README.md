# Local operational monitoring

This opt-in Linux setup uses host networking to reach the application's
loopback listeners. It binds monitoring listeners only to 127.0.0.1. Start the
QA stack (`make qa`) and, in another terminal:

```bash
docker compose -f monitoring/compose.yml up -d
```

Open `http://127.0.0.1:9090`. Blackbox probes monitor both applications' `/health`
endpoints. For API request counters/histograms, start normal backend development
with `ENABLE_METRICS=true` and the same port, or export it before `make qa`.
Keep `/metrics` behind a trusted network boundary in any deployed environment.

Useful Prometheus queries for deployment impact:

```promql
sum by (route, status) (rate(pnid_http_requests_total[5m]))
histogram_quantile(0.95, sum by (le, route) (rate(pnid_http_request_duration_seconds_bucket[5m])))
sum by (event_type) (rate(pnid_frontend_events_total[5m]))
probe_success{job="application-health"}
```

The `pnid_frontend_events_total` counter comes from `POST /api/events`: the
browser reports allowlisted feature events (uploads, detection, chat) so
frontend behavior is observable next to backend HTTP metrics. Payloads carry
only the event name and an optional coarse status; nothing user-identifying.

Alerts cover failing frontend/backend health probes, elevated API 5xx rate,
and p95 API latency. `make monitoring-check` validates the Prometheus config,
rule syntax, and alert behavior using promtool in the pinned Prometheus image.
No notification receiver or production scrape destination is invented here.
Connect your real Alertmanager/on-call receiver before relying on paging.

Stop only these monitoring services with:

```bash
docker compose -f monitoring/compose.yml down
```

This setup is Linux-only; do not expose the backend on a public interface just
to make host-network scraping work on another OS.
