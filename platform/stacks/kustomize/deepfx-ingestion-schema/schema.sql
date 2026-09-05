CREATE DATABASE IF NOT EXISTS deepfx;

CREATE TABLE IF NOT EXISTS deepfx.ticks
(
    symbol        LowCardinality(String),
    bid           Float64,
    ask           Float64,
    last          Float64,
    volume        Float64,
    spread        Float64 MATERIALIZED ask - bid,
    mid           Float64 MATERIALIZED (bid + ask) / 2,
    time          DateTime64(3, 'UTC'),
    time_msc      Int64,
    received_at   DateTime64(3, 'UTC') DEFAULT now64(3),


    INDEX idx_symbol symbol TYPE bloom_filter GRANULARITY 1,
    INDEX idx_time time TYPE minmax GRANULARITY 1
)
ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(time)
ORDER BY (symbol, time, time_msc)
TTL toDateTime(time) + INTERVAL 90 DAY
SETTINGS index_granularity = 8192
COMMENT 'Real-time FX tick data from MT5';

CREATE TABLE IF NOT EXISTS deepfx.ohlcv
(
    symbol        LowCardinality(String),
    timeframe     LowCardinality(String),
    time          DateTime('UTC'),
    open          Float64,
    high          Float64,
    low           Float64,
    close         Float64,
    volume        Float64,
    tick_volume   UInt64,
    spread        Int32,
    received_at   Nullable(DateTime64(3, 'UTC')) DEFAULT NULL,


    body          Float64 MATERIALIZED abs(close - open),
    upper_wick    Float64 MATERIALIZED high - greatest(open, close),
    lower_wick    Float64 MATERIALIZED least(open, close) - low,
    is_bullish    UInt8 MATERIALIZED close > open,


    INDEX idx_symbol symbol TYPE bloom_filter GRANULARITY 1,
    INDEX idx_timeframe timeframe TYPE bloom_filter GRANULARITY 1
)
ENGINE = ReplacingMergeTree()
PARTITION BY (timeframe, toYYYYMM(time))
ORDER BY (symbol, timeframe, time)
TTL time + INTERVAL 5 YEAR
SETTINGS index_granularity = 8192
COMMENT 'OHLCV candlestick data aggregated by timeframe';

CREATE TABLE IF NOT EXISTS deepfx.ticks_queue
(
    symbol        String,
    bid           Float64,
    ask           Float64,
    last          Float64,
    volume        Float64,
    time          String,
    time_msc      Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'SASL_SSL://redpanda.redpanda.svc:9093',
    kafka_topic_list  = 'deepfx.market.tick',
    kafka_group_name  = 'ch.homelab.deepfx.ticks',
    kafka_format      = 'JSONEachRow',
    kafka_num_consumers = 1,
    kafka_max_block_size = 65536,
    kafka_skip_broken_messages = 1,
    kafka_handle_error_mode = 'stream',
    kafka_thread_per_consumer = 0;

CREATE MATERIALIZED VIEW IF NOT EXISTS deepfx.ticks_mv TO deepfx.ticks AS
SELECT
    symbol,
    bid,
    ask,
    last,
    volume,
    coalesce(parseDateTime64BestEffortOrNull(time, 3, 'UTC'), now64(3)) AS time,
    time_msc,
    now64(3) AS received_at
FROM deepfx.ticks_queue;

CREATE TABLE IF NOT EXISTS deepfx.ohlcv_queue
(
    symbol        String,
    timeframe     String,
    time          String,
    open          Float64,
    high          Float64,
    low           Float64,
    close         Float64,
    volume        Float64,
    tick_volume   UInt64,
    spread        Int32
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'SASL_SSL://redpanda.redpanda.svc:9093',
    kafka_topic_list  = 'deepfx.market.ohlcv',
    kafka_group_name  = 'ch.homelab.deepfx.ohlcv',
    kafka_format      = 'JSONEachRow',
    kafka_num_consumers = 1,
    kafka_max_block_size = 65536,
    kafka_skip_broken_messages = 1,
    kafka_handle_error_mode = 'stream';

CREATE MATERIALIZED VIEW IF NOT EXISTS deepfx.ohlcv_mv TO deepfx.ohlcv AS
SELECT
    symbol,
    timeframe,
    coalesce(parseDateTime64BestEffortOrNull(time, 0, 'UTC'), now()) AS time,
    open,
    high,
    low,
    close,
    volume,
    tick_volume,
    spread,
    now64(3) AS received_at
FROM deepfx.ohlcv_queue;

CREATE TABLE IF NOT EXISTS deepfx.market_features
(

    symbol        LowCardinality(String),


    event_time    DateTime64(3, 'UTC'),
    time_msc      Int64,


    kind          LowCardinality(String),


    timeframe     LowCardinality(String) DEFAULT '',


    mid           Float64 DEFAULT 0,
    spread        Float64 DEFAULT 0,
    spread_pct    Float64 DEFAULT 0,
    tick_rate     Float64 DEFAULT 0,
    pressure      Float64 DEFAULT 0,
    tick_return   Float64 DEFAULT 0,


    open          Float64 DEFAULT 0,
    high          Float64 DEFAULT 0,
    low           Float64 DEFAULT 0,
    close         Float64 DEFAULT 0,
    volume        Float64 DEFAULT 0,
    ohlcv_return  Float64 DEFAULT 0,
    ohlcv_range   Float64 DEFAULT 0,


    received_at   DateTime64(3, 'UTC') DEFAULT now64(3),


    INDEX idx_symbol symbol TYPE bloom_filter GRANULARITY 1,
    INDEX idx_kind kind TYPE bloom_filter GRANULARITY 1,
    INDEX idx_event_time event_time TYPE minmax GRANULARITY 1
)
ENGINE = MergeTree()
PARTITION BY (kind, toYYYYMMDD(event_time))
ORDER BY (symbol, kind, timeframe, event_time, time_msc)
TTL toDateTime(event_time) + INTERVAL 90 DAY
SETTINGS index_granularity = 8192
COMMENT 'Computed market features for Feast offline store';

CREATE TABLE IF NOT EXISTS deepfx.market_features_queue
(
    schema        String,
    kind          String,
    ts            String,
    symbol        String,
    time_msc      Int64,
    timeframe     String,
    time          String,
    features      String
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'SASL_SSL://redpanda.redpanda.svc:9093',
    kafka_topic_list  = 'deepfx.market.feature.latest',
    kafka_group_name  = 'ch.homelab.deepfx.features',
    kafka_format      = 'JSONEachRow',
    kafka_num_consumers = 1,
    kafka_max_block_size = 65536,
    kafka_skip_broken_messages = 1,
    kafka_handle_error_mode = 'stream';

CREATE MATERIALIZED VIEW IF NOT EXISTS deepfx.market_features_mv TO deepfx.market_features AS
SELECT
    symbol,
    coalesce(parseDateTime64BestEffortOrNull(ts, 3, 'UTC'), now64(3)) AS event_time,
    time_msc,
    kind,
    coalesce(timeframe, '') AS timeframe,


    JSONExtractFloat(features, 'mid') AS mid,
    JSONExtractFloat(features, 'spread') AS spread,
    JSONExtractFloat(features, 'spread_pct') AS spread_pct,
    JSONExtractFloat(features, 'tick_rate') AS tick_rate,
    JSONExtractFloat(features, 'pressure') AS pressure,
    JSONExtractFloat(features, 'return') AS tick_return,


    JSONExtractFloat(features, 'open') AS open,
    JSONExtractFloat(features, 'high') AS high,
    JSONExtractFloat(features, 'low') AS low,
    JSONExtractFloat(features, 'close') AS close,
    JSONExtractFloat(features, 'volume') AS volume,
    if(kind = 'ohlcv', JSONExtractFloat(features, 'return'), 0) AS ohlcv_return,
    JSONExtractFloat(features, 'range') AS ohlcv_range,

    now64(3) AS received_at
FROM deepfx.market_features_queue;

CREATE VIEW IF NOT EXISTS deepfx.latest_tick_features AS
SELECT
    symbol,
    event_time,
    mid,
    spread,
    spread_pct,
    tick_rate,
    pressure,
    tick_return
FROM deepfx.market_features
WHERE kind = 'tick'
ORDER BY symbol, event_time DESC
LIMIT 1 BY symbol;

CREATE VIEW IF NOT EXISTS deepfx.latest_ohlcv_features AS
SELECT
    symbol,
    timeframe,
    event_time,
    open,
    high,
    low,
    close,
    volume,
    ohlcv_return,
    ohlcv_range
FROM deepfx.market_features
WHERE kind = 'ohlcv'
ORDER BY symbol, timeframe, event_time DESC
LIMIT 1 BY symbol, timeframe;

CREATE TABLE IF NOT EXISTS deepfx.trade_event_archive
(
    kst_date             Date,
    ts                   DateTime64(6, 'UTC'),
    id                   UUID,
    run_id               UUID,
    idempotency_key      String,
    request_id           Nullable(String),
    correlation_id       UUID,
    sequence             Int64,
    symbol               LowCardinality(String),
    timeframe            Nullable(String),
    event_type           LowCardinality(String),
    side                 Nullable(String),
    confidence           Nullable(Float64),
    reason               String,
    comment              Nullable(String),
    position_id          Nullable(Int64),
    sl_price             Nullable(Float64),
    tp_price             Nullable(Float64),
    entry_price          Nullable(Float64),
    volume_requested     Nullable(Float64),
    volume_final         Nullable(Float64),
    strategy_instance_id Nullable(String),
    strategy_version     Nullable(String),
    mode                 LowCardinality(String),
    source               LowCardinality(String),
    created_at           DateTime64(6, 'UTC'),
    updated_at           DateTime64(6, 'UTC'),
    snapshot_json        String,
    snapshot_sha256      FixedString(64),
    archive_exported_at  DateTime64(3, 'UTC'),
    archive_kst_date     Date,
    archive_schema_ver   UInt16 DEFAULT 1
)
ENGINE = ReplacingMergeTree()
PARTITION BY toYYYYMM(kst_date)
ORDER BY (kst_date, coalesce(strategy_instance_id, ''), symbol, ts, id)
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS deepfx.run_archive
(
    kst_date             Date,
    id                   UUID,
    started_at           DateTime64(6, 'UTC'),
    ended_at             Nullable(DateTime64(6, 'UTC')),
    strategy_instance_id LowCardinality(String),
    strategy_version     Nullable(String),
    config_json          String,
    config_sha256        FixedString(64),
    pod_name             Nullable(String),
    node_name            Nullable(String),
    archive_exported_at  DateTime64(3, 'UTC'),
    archive_kst_date     Date,
    archive_schema_ver   UInt16 DEFAULT 1
)
ENGINE = ReplacingMergeTree()
PARTITION BY toYYYYMM(kst_date)
ORDER BY (kst_date, strategy_instance_id, started_at, id)
SETTINGS index_granularity = 8192;
