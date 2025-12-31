# Observability Stack

Kubernetes-native platform for logging, metrics, tracing, and APM.

## Architecture

![Observability Stack](./observability-stack.svg)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Data Flow                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Logs:    Pods → Vector → VRL Filter → Redpanda → Quickwit → Grafana            │
│  Metrics: OTel SDK → Alloy → VictoriaMetrics → Grafana                          │
│  Traces:  OTel SDK → Alloy → Tempo → Grafana                                    │
│  APM:     Pyroscope (service map, trace-log correlation)                        │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Stack Components

### Collection Layer

| Component | Role | Function |
|-----------|------|----------|
| Vector | DaemonSet log collector | Collects k8s_logs, applies VRL transforms |
| Grafana Alloy | OTel Collector | Receives OTLP (traces + metrics), batches, forwards |
| Prometheus | Metrics scraper | node-exporter, cilium, app /metrics endpoints |

### Storage Layer

| Component | Role | Protocol |
|-----------|------|----------|
| Redpanda | Message queue | Kafka API (SASL_SSL + SCRAM) |
| Quickwit | Log search engine | Tantivy-based, S3 backend |
| VictoriaMetrics | Time series DB | PromQL |
| Tempo | Trace storage | TraceQL |
| MinIO | Object storage | S3 API (quickwit-data bucket) |

### Visualization Layer

| Component | Role | Datasources |
|-----------|------|-------------|
| Grafana | Dashboards, Explore, Alerting | Quickwit, VictoriaMetrics, Tempo |
| Pyroscope | APM | Service map, trace-log correlation, error analysis |

## Quickwit Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Indexer    │     │   Searcher   │     │  Metastore   │
│              │     │              │     │              │
│  Redpanda    │     │  HTTP :7280  │     │     MinIO    │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │
                    ┌───────▼──────┐
                    │     MinIO     │
                    │ quickwit-data │
                    └───────────────┘
```

## Vector Configuration

VRL filter applied to all logs:

- Drop `kube-system`, `monitoring` namespaces
- Flatten `k8s.*` fields
- Forward to Redpanda topic: `logs.k8s.all`

## Log Storage Strategy

Quickwit batches data before indexing (optimized for throughput, not real-time).

| Tier | Storage | Retention | Use Case |
|------|---------|-----------|----------|
| Hot | VictoriaLogs | 24h | Live tailing, debugging |
| Cold | Quickwit | Long-term | Analytics, compliance |

## Alerting

| Source | Engine | Destination |
|--------|--------|-------------|
| Logs | Vector filters | Slack (Realtime) |
| Metrics | vmalert (PromQL) | Alertmanager → Slack |

## Grafana Datasources

```yaml
datasources:
  - name: Quickwit
    type: quickwit
    url: http://quickwit-searcher:7280

  - name: Prometheus
    type: prometheus
    url: http://victoria-metrics:8428

  - name: Tempo
    type: tempo
    url: http://tempo:3100
```

## Related Docs

- [System Architecture](./architecture.md)
- [Feature Store](./feature-store.md)
