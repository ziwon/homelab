# Homelab

## NVIDIA + Ray Hybrid Architecture
Details are [gpu-partitioning-architecture.md](./gpu-partitioning-architecture.md/)

``` 
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        Host: Intel Core Ultra 9 285K                            │
│                        RAM: 128GB DDR5 | GPU: RTX 5080 16GB                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         Docker Environment                               │   │
│  │                                                                          │   │
│  │  ┌────────────────────┐    ┌───────────────────────────────────────────┐ │   │
│  │  │   nvidia-mps       │    │              ray-node                     │ │   │
│  │  │   Container        │    │              Container                    │ │   │
│  │  │                    │    │                                           │ │   │
│  │  │  ┌──────────────┐  │    │  ┌─────────────────────────────────────┐  │ │   │
│  │  │  │ MPS Control  │  │    │  │           Ray Cluster               │  │ │   │
│  │  │  │   Daemon     │◄─┼────┼──┤                                     │  │ │   │
│  │  │  └──────────────┘  │    │  │  ┌─────────┐     ┌───────────────┐  │  │ │   │
│  │  │         │          │    │  │  │Ray Head │     │  Ray Worker   │  │  │ │   │
│  │  │         ▼          │    │  │  │(E-cores)│     │  (P-cores)    │  │  │ │   │
│  │  │  ┌──────────────┐  │    │  │  │         │     │               │  │  │ │   │
│  │  │  │ /mps/pipe    │◄─┼────┼──┤  │ CPU_E:16│     │ CPU_P: 8      │  │  │ │   │
│  │  │  │ (Unix Socket)│  │    │  │  │ num_cpu:0     │ num_gpus: 16  │  │  │ │   │
│  │  │  └──────────────┘  │    │  │  └─────────┘     │ VRAM_GB: 16   │  │  │ │   │
│  │  │                    │    │  │                  └───────────────┘  │  │ │   │
│  │  └────────────────────┘    │  └─────────────────────────────────────┘  │ │   │
│  │                            └───────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Feature Store Architecture

- Market features for fundamental analysis will be added.

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           DeepFX Feature Store Architecture                             │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  DATA INGESTION                                                                         │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│   ┌──────────────┐         ┌─────────────────┐         ┌──────────────────────┐         │
│   │   MT5-Bridge │────────▶│    Redpanda     │────────▶│    Feature-Engine    │         │
│   │   (ZeroMQ)   │         │    (Kafka)      │         │    (Python/asyncio)  │         │
│   └──────────────┘         ├─────────────────┤         └──────────┬───────────┘         │
│                            │ deepfx.market.  │                    │                     │
│                            │   tick          │                    │ Compute:            │
│                            │   ohlcv         │                    │ - spread_pct        │
│                            └─────────────────┘                    │ - pressure          │
│                                                                   │ - tick_rate         │
│                                                                   │ - returns           │
└───────────────────────────────────────────────────────────────────┼─────────────────────┘
                                                                    │
                              ┌─────────────────────────────────────┼──────────────────┐
                              │                                     ▼                  │
                              │                          ┌──────────────────┐          │
                              │                          │   Feast Push API │          │
                              │                          │  store.push()    │          │
                              │                          └────────┬─────────┘          │
                              │                                   │                    │
                              │                    ┌──────────────┴──────────────┐     │
                              │                    ▼                             ▼     │
┌─────────────────────────────┼────────────────────────────────┐ ┌─────────────────────┼───┐
│  ONLINE STORE (Real-time)   │                                │ │ OFFLINE STORE       │   │
├─────────────────────────────┼────────────────────────────────┤ ├─────────────────────┼───┤
│                             │                                │ │ (Historical)        │   │
│  ┌────────────────────────┐ │                                │ │                     │   │
│  │        Redis           │◀┘                                │ │ ┌─────────────────┐ │   │
│  │  redis.redis.svc:6379  │                                  │ │ │   ClickHouse    │◀┘   │
│  └────────────────────────┘                                  │ │ │ clickhouse:8123 │     │
│                                                              │ │ └─────────────────┘     │
│  Keys (TTL: 1 min):                                          │ │                         │
│  ├─ deepfx:feature:XAUUSD   (STRING, 3KB)                    │ │ Tables:                 │
│  ├─ deepfx:feature:BTCUSD   (STRING, 3KB)                    │ │ ├─ market_features      │
│  ├─ deepfx:feature:NAS100   (STRING, 3KB)                    │ │ ├─ market_features_mv   │
│  └─ deepfx:feature:USOUSD   (STRING, 2KB)                    │ │ ├─ market_features_queue│
│                                                              │ │ ├─ latest_tick_features │
│  Feast Internal (No TTL):                                    │ │ ├─ latest_ohlcv_features│
│  ├─ symbol XAUUSDhomelab    (HASH, 384B)                     │ │ ├─ ticks / ticks_mv     │
│  ├─ symbol BTCUSDhomelab    (HASH, 376B)                     │ │ └─ ohlcv / ohlcv_mv     │
│  ├─ symbol NAS100homelab    (HASH, 384B)                     │ │                         │
│  └─ symbol USOUSDhomelab    (HASH, 384B)                     │ │ Database: deepfx        │
│                                                              │ │                         │
│  Latency: < 1ms                                              │ │ Latency: 10-100ms       │
└──────────────────────────────────────────────────────────────┘ └─────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  FEAST REGISTRY (Metadata)                                                              │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│   ┌────────────────────────────────────────────────────────────────────────────────┐    │
│   │                         PostgreSQL (cluster-pg-db:5432)                        │    │
│   │                              Database: deepfx                                  │    │
│   └────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                         │
│   Project: homelab                                                                      │
│   Entity Key Serialization: v3                                                          │
│   Cache TTL: 60 seconds                                                                 │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  FEAST LINEAGE (Feature Definitions)                                                    │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│   ┌─────────────────────┐                      ┌─────────────────────────────────────┐  │
│   │    DATA SOURCES     │                      │          FEATURE VIEWS              │  │
│   │    (ClickHouse)     │                      │          (with Push)                │  │
│   └─────────────────────┘                      └─────────────────────────────────────┘  │
│                                                                                         │
│   ┌─────────────────────┐       ┌────────┐     ┌─────────────────────────────────────┐  │
│   │ tick_features_source│──────▶│ symbol │────▶│ tick_features                [P]    │  │
│   │ (market_features    │       │(Entity)│     │                                     │  │
│   │  kind='tick')       │       │        │     │ • time_msc     (Int64)              │  │
│   └─────────────────────┘       │        │     │ • mid          (Float64)            │  │
│            ▲                    │        │     │ • spread       (Float64)            │  │
│            │                    │        │     │ • spread_pct   (Float64)            │  │
│   ┌────────┴────────────┐       │        │     │ • tick_rate    (Float64)            │  │
│   │ tick_push_source    │       │        │     │ • pressure     (Float64)            │  │
│   │ (PushSource)        │       │        │     │ • tick_return  (Float64)            │  │
│   └─────────────────────┘       │        │     │                                     │  │
│                                 │        │     │ TTL: 120s  |  Update: 200ms         │  │
│                                 │        │     └─────────────────────────────────────┘  │
│                                 │        │                                              │
│   ┌─────────────────────┐       │        │     ┌─────────────────────────────────────┐  │
│   │ohlcv_features_source│──────▶│        │────▶│ ohlcv_features               [P]    │  │
│   │ (market_features    │       │        │     │                                     │  │
│   │  kind='ohlcv')      │       └────────┘     │ • timeframe    (String)             │  │
│   └─────────────────────┘                      │ • open/high/low/close (Float64)     │  │
│            ▲                                   │ • volume       (Float64)            │  │
│            │                                   │ • ohlcv_return (Float64)            │  │
│   ┌────────┴────────────┐                      │ • ohlcv_range  (Float64)            │  │
│   │ ohlcv_push_source   │                      │                                     │  │
│   │ (PushSource)        │                      │ TTL: 3600s |  Update: per bar       │  │
│   └─────────────────────┘                      └─────────────────────────────────────┘  │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  CONSUMERS                                                                              │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│   ┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────────┐   │
│   │   Strategy-Engine   │     │    Nightly-Dream    │     │      ML Training        │   │
│   │   (Real-time)       │     │    (Backtest)       │     │      (Historical)       │   │
│   └──────────┬──────────┘     └──────────┬──────────┘     └───────────┬─────────────┘   │
│              │                           │                            │                 │
│              ▼                           ▼                            ▼                 │
│   ┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────────┐   │
│   │ get_online_features │     │get_historical_features    │ get_historical_features │   │
│   │ (Redis < 1ms)       │     │ (ClickHouse)        │     │ (ClickHouse)            │   │
│   └─────────────────────┘     └─────────────────────┘     └─────────────────────────┘   │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  CURRENT DATA STATUS (2025-12-18 04:16 UTC)                                             │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│   Symbols Active: XAUUSD, BTCUSD, NAS100, USOUSD                                        │
│   Timeframes:     M1, M5, M15, H1, H4, D1                                               │
│                                                                                         │
│   ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│   │ latest_tick_features    │  4 rows   │  ~10 ticks/sec per symbol                  │  │
│   │ latest_ohlcv_features   │  24 rows  │  4 symbols × 6 timeframes                  │  │
│   └──────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

## Observability Stack

> Disclaimer: This document is currently in active development.

This document describes the observability stack architecture for the homelab, designed as a Kubernetes-native platform for logging, metrics, and tracing. 

![Observability Stack Architecture](./observability-stack.svg)

### Architecture Overview

The stack is composed of three main layers: **Collection**, **Storage & Streaming**, and **Visualization & Analysis**.

#### 1. Kubernetes Cluster (Collection Layer)

This layer is responsible for gathering telemetry data from application pods and infrastructure.

*   **Application Pods**:
    *   Components: `api-gateway`, `backend`, `jobs`.
    *   Outputs: `stdout/stderr` (logs), JSON logs, OTel SDK (traces + metrics).
*   **Vector**:
    *   Role: DaemonSet Log Collector.
    *   Function: Collects `k8s_logs` and forwards them.
    *   **VRL Filter**: Applies transformations such as dropping `kube-system` and `monitoring` namespaces, and flattening `k8s.*` fields.
*   **Grafana Alloy (OTel Collector)**:
    *   Role: OpenTelemetry Collector.
    *   Function: Receives OTLP data (traces & metrics), batches it, and forwards it to storage backends.
*   **Prometheus Scrape Targets**:
    *   Sources: `node-exporter`, `cilium metrics`, app metrics (`/metrics`).
    *   Method: `remote_write` to storage.

#### 2. Message Queue & Storage

This layer handles the persistence and buffering of telemetry data.

*   **Redpanda**:
    *   Role: Kafka-compatible Message Queue.
    *   Topic: `logs.k8s.all`.
    *   Auth: SASL_SSL + SCRAM.
    *   Function: Buffers logs from Vector before indexing.
*   **Quickwit**:
    *   Role: Cloud-native Log Search Engine.
    *   Components:
        *   **Indexer**: Consumes from Kafka (Redpanda).
        *   **Searcher**: Serves queries via HTTP (`:7280`).
        *   **Metastore**: Stores metadata in MinIO.
    *   Tags: Tantivy, k8s-logs.
*   **VictoriaMetrics**:
    *   Role: Time Series Database (PromQL).
    *   Function: Stores metrics from Alloy and Prometheus targets.
*   **Tempo**:
    *   Role: Distributed Tracing (TraceQL).
    *   Function: Stores traces from Alloy.
*   **MinIO**:
    *   Role: S3-compatible Object Storage.
    *   Bucket: `quickwit-data`.
    *   Function: Backend storage for Quickwit.

#### 3. Visualization & Analysis

This layer provides the user interface for monitoring and debugging.

*   **Grafana**:
    *   Role: Unified Observability Dashboard.
    *   Features:
        *   **Dashboards**: Custom panels.
        *   **Explore**: Ad-hoc queries for Logs, Metrics, and Traces.
        *   **Alerting**: Rules and notifications.
    *   **Datasources**:
        *   Quickwit (Logs)
        *   Prometheus (Metrics - via VictoriaMetrics)
        *   Tempo (Traces)
*   **Pyroscope APM**:
    *   Role: Application Performance Monitoring.
    *   Features:
        *   **Service Map**: Visualizes dependencies.
        *   **Trace -> Logs**: Correlates traces with logs.
        *   **Error Analysis**: Root cause analysis.

### Data Flow Summary

*   **Logs Flow**:
    `Pods` -> `Vector` -> `VRL Filter` -> `Redpanda` -> `Quickwit` -> `Grafana`
*   **Metrics Flow**:
    `OTel SDK` -> `Alloy` -> `VictoriaMetrics` -> `Grafana`
*   **Traces Flow**:
    `OTel SDK` -> `Alloy` -> `Tempo` -> `Grafana`

### Real-time Log Search Considerations

Quickwit is designed for high-volume, cost-efficient log storage on object storage (like S3/MinIO). By design, it batches data before indexing and uploading to object storage to optimize for throughput and storage costs. This architecture introduces a small ingestion latency (typically seconds to minutes), meaning it does not support true real-time "tailing" of logs.

To address this, we implement a **Hybrid Storage Strategy**:
*   **Hot Storage (Loki or VictoriaLogs)**: Used for real-time log ingestion and "live tailing" (e.g., last 24 hours). This provides immediate visibility for debugging.
*   **Cold Storage (Quickwit)**: Used for long-term retention and high-volume analytics. Logs are archived here for cost-efficiency.
