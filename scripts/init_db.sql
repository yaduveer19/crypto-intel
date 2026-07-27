CREATE EXTENSION IF NOT EXISTS timescaledb;

-- OHLC candles
CREATE TABLE IF NOT EXISTS ohlc (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume DOUBLE PRECISION,
    exchange VARCHAR(10) DEFAULT 'binance'
);
SELECT create_hypertable('ohlc', 'time', if_not_exists => TRUE);

-- Funding rate
CREATE TABLE IF NOT EXISTS funding_rate (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    rate DOUBLE PRECISION,
    exchange VARCHAR(10) DEFAULT 'binance'
);
SELECT create_hypertable('funding_rate', 'time', if_not_exists => TRUE);

-- Open Interest
CREATE TABLE IF NOT EXISTS open_interest (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    oi DOUBLE PRECISION,
    oi_usd DOUBLE PRECISION,
    exchange VARCHAR(10) DEFAULT 'binance'
);
SELECT create_hypertable('open_interest', 'time', if_not_exists => TRUE);

-- Liquidation data
CREATE TABLE IF NOT EXISTS liquidations (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10),
    amount DOUBLE PRECISION,
    price DOUBLE PRECISION,
    exchange VARCHAR(10) DEFAULT 'binance'
);
SELECT create_hypertable('liquidations', 'time', if_not_exists => TRUE);

-- News / Narrative
CREATE TABLE IF NOT EXISTS news (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL,
    source VARCHAR(50),
    title TEXT,
    url TEXT,
    sentiment VARCHAR(10),
    sentiment_score DOUBLE PRECISION DEFAULT 0
);

-- Lane outputs
CREATE TABLE IF NOT EXISTS lane_outputs (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    lane VARCHAR(20) NOT NULL,
    bias VARCHAR(10),
    tier VARCHAR(10),
    signals JSONB,
    raw_data JSONB
);
SELECT create_hypertable('lane_outputs', 'time', if_not_exists => TRUE);

-- Final Verdicts
CREATE TABLE IF NOT EXISTS verdicts (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    bias VARCHAR(10),
    tier VARCHAR(10),
    entry_price DOUBLE PRECISION,
    stop_loss DOUBLE PRECISION,
    tp1 DOUBLE PRECISION,
    tp2 DOUBLE PRECISION,
    reasoning TEXT,
    lane_breakdown JSONB
);
SELECT create_hypertable('verdicts', 'time', if_not_exists => TRUE);

-- Historical accuracy tracking per lane
CREATE TABLE IF NOT EXISTS lane_accuracy (
    lane VARCHAR(20) PRIMARY KEY,
    total_predictions INTEGER DEFAULT 0,
    correct_predictions INTEGER DEFAULT 0,
    win_rate DOUBLE PRECISION DEFAULT 0.5,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO lane_accuracy (lane, total_predictions, correct_predictions, win_rate)
VALUES ('technical', 100, 55, 0.55),
       ('flow', 100, 52, 0.52),
       ('narrative', 100, 48, 0.48),
       ('macro', 100, 50, 0.50)
ON CONFLICT (lane) DO NOTHING;

-- Portfolio / Position tracking for simulator
CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10),
    entry_price DOUBLE PRECISION,
    size DOUBLE PRECISION,
    stop_loss DOUBLE PRECISION,
    take_profit1 DOUBLE PRECISION,
    take_profit2 DOUBLE PRECISION,
    status VARCHAR(20) DEFAULT 'open',
    opened_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ
);
