# Feature Store

Feast-based ML feature platform for real-time and historical feature serving.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           DeepFX Feature Store Architecture                             │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  DATA INGESTION                                                                         │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│   ┌──────────────┐         ┌─────────────────┐         ┌──────────────────────┐         │
│   │   MT5-Bridge │───────▶│    Redpanda      │───────▶ │    Feature-Engine    │         │
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
                                                                    ▼
                                                          ┌──────────────────┐
                                                          │   Feast Push API │
                                                          │  store.push()    │
                                                          └────────┬─────────┘
                                                                   │
                                                ┌──────────────────┴──────────────────┐
                                                ▼                                     ▼
┌──────────────────────────────────────────────────────────┐ ┌───────────────────────────────┐
│  ONLINE STORE (Real-time)                                │ │  OFFLINE STORE (Historical)   │
├──────────────────────────────────────────────────────────┤ ├───────────────────────────────┤
│                                                          │ │                               │
│  ┌────────────────────────┐                              │ │  ┌─────────────────┐          │
│  │        Redis           │                              │ │  │   ClickHouse    │          │
│  │  redis.redis.svc:6379  │                              │ │  │ clickhouse:8123 │          │
│  └────────────────────────┘                              │ │  └─────────────────┘          │
│                                                          │ │                               │
│  Keys (TTL: 1 min):                                      │ │  Tables:                      │
│  ├─ deepfx:feature:XAUUSD   (STRING, 3KB)                │ │  ├─ market_features           │
│  ├─ deepfx:feature:BTCUSD   (STRING, 3KB)                │ │  ├─ market_features_mv        │
│  ├─ deepfx:feature:NAS100   (STRING, 3KB)                │ │  ├─ latest_tick_features      │
│  └─ deepfx:feature:USOUSD   (STRING, 2KB)                │ │  ├─ latest_ohlcv_features     │
│                                                          │ │  └─ ticks / ohlcv             │
│  Latency: < 1ms                                          │ │                               │
│                                                          │ │  Latency: 10-100ms            │
└──────────────────────────────────────────────────────────┘ └───────────────────────────────┘
```

## Components

| Component | Role | Latency |
|-----------|------|---------|
| Redis | Online store for real-time serving | < 1ms |
| ClickHouse | Offline store for historical queries | 10-100ms |
| PostgreSQL | Feast registry (metadata) | - |
| Redpanda | Event streaming (Kafka API) | - |

## Feature Views

### Tick Features

Real-time market tick data with computed features.

| Field | Type | Description |
|-------|------|-------------|
| time_msc | Int64 | Timestamp (milliseconds) |
| mid | Float64 | Mid price |
| spread | Float64 | Bid-ask spread |
| spread_pct | Float64 | Spread as percentage |
| tick_rate | Float64 | Ticks per second |
| pressure | Float64 | Buy/sell pressure |
| tick_return | Float64 | Price return |

- TTL: 120s
- Update interval: 200ms

### OHLCV Features

Candlestick data across multiple timeframes.

| Field | Type | Description |
|-------|------|-------------|
| timeframe | String | M1, M5, M15, H1, H4, D1 |
| open/high/low/close | Float64 | OHLC prices |
| volume | Float64 | Trade volume |
| ohlcv_return | Float64 | Bar return |
| ohlcv_range | Float64 | High-low range |

- TTL: 3600s
- Update interval: per bar close

## Consumers

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   Strategy-Engine   │     │    Nightly-Dream    │     │      ML Training    │
│   (Real-time)       │     │    (Backtest)       │     │      (Historical)   │
└──────────┬──────────┘     └──────────┬──────────┘     └──────────┬──────────┘
           │                           │                           │
           ▼                           ▼                           ▼
  get_online_features        get_historical_features    get_historical_features
       (Redis)                    (ClickHouse)               (ClickHouse)
```

## Usage

```python
from feast import FeatureStore

store = FeatureStore(repo_path=".")

# Real-time features
online_features = store.get_online_features(
    features=["tick_features:spread_pct", "tick_features:pressure"],
    entity_rows=[{"symbol": "XAUUSD"}]
)

# Historical features for training
historical_features = store.get_historical_features(
    features=["ohlcv_features:ohlcv_return"],
    entity_df=entity_df
)
```

## Registry

| Setting | Value |
|---------|-------|
| Project | homelab |
| Database | deepfx (PostgreSQL) |
| Entity Key Serialization | v3 |
| Cache TTL | 60s |

## Active Symbols

| Symbol | Type |
|--------|------|
| XAUUSD | Gold |
| BTCUSD | Bitcoin |
| NAS100 | Nasdaq 100 |
| USOUSD | Crude Oil |

Timeframes: M1, M5, M15, H1, H4, D1

## Related Docs

- [System Architecture](./architecture.md)
- [GPU Partitioning](./gpu-partitioning.md)
