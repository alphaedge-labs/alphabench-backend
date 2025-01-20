-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE,
    google_id VARCHAR(255) UNIQUE,
    is_anonymous BOOLEAN NOT NULL DEFAULT false,
    ip_address VARCHAR(45),
    mac_address VARCHAR(17),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Subscription plans table
CREATE TABLE IF NOT EXISTS subscription_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price_usd DECIMAL(10, 2) NOT NULL,
    reports_per_day INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User subscriptions table
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    plan_id UUID NOT NULL REFERENCES subscription_plans(id),
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Backtest requests table
CREATE TABLE IF NOT EXISTS backtest_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    instrument_symbol VARCHAR(20) NOT NULL,
    from_date DATE NOT NULL,
    to_date DATE NOT NULL,
    strategy_description TEXT NOT NULL,
    strategy_title VARCHAR(255),
    python_script_url TEXT,
    validation_data_url TEXT,
    full_data_url TEXT,
    log_file_url TEXT,
    report_url TEXT,
    ready_for_report BOOLEAN NOT NULL DEFAULT false,
    generated_report BOOLEAN NOT NULL DEFAULT false,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Daily report counts table for rate limiting
CREATE TABLE IF NOT EXISTS daily_report_counts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, date)
);

CREATE TABLE IF NOT EXISTS waitlist_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    metadata JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Historical data
CREATE TABLE IF NOT EXISTS tick_data (
    time TIMESTAMPTZ NOT NULL,
    ticker TEXT NOT NULL,
    price DOUBLE PRECISION,
    volume BIGINT,
    exchange TEXT,
    bid_price DOUBLE PRECISION,
    ask_price DOUBLE PRECISION,
    bid_size BIGINT,
    ask_size BIGINT,
    trade_condition TEXT,
    vwap DOUBLE PRECISION,
    market_cap DOUBLE PRECISION,
    spread DOUBLE PRECISION,
    moving_avg_5min DOUBLE PRECISION,
    moving_avg_15min DOUBLE PRECISION,
    relative_strength_index DOUBLE PRECISION,
    macd DOUBLE PRECISION,
    bollinger_upper DOUBLE PRECISION,
    bollinger_lower DOUBLE PRECISION,
    trade_id TEXT,
    order_id TEXT,
    sector TEXT,
    industry TEXT,
    company_name TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    price_change DOUBLE PRECISION,
    price_change_pct DOUBLE PRECISION,
    cumulative_volume BIGINT,
    daily_high DOUBLE PRECISION,
    daily_low DOUBLE PRECISION,
    is_anomaly BOOLEAN DEFAULT FALSE,
    sentiment_score DOUBLE PRECISION,
    news_event TEXT,
    latency INTERVAL,
    data_quality_score DOUBLE PRECISION,
    momentum DOUBLE PRECISION,
    adx DOUBLE PRECISION,
    stochastic_k DOUBLE PRECISION,
    stochastic_d DOUBLE PRECISION,
    buy_orders BIGINT,
    sell_orders BIGINT,
    open_interest BIGINT,
    currency_pair TEXT,
    fx_rate DOUBLE PRECISION,
    custom_metric_1 DOUBLE PRECISION,
    custom_metric_2 DOUBLE PRECISION,
    data_source TEXT,
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

-- Create indexes
CREATE INDEX idx_users_google_id ON users(google_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_backtest_requests_user_id ON backtest_requests(user_id);
CREATE INDEX idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX idx_daily_report_counts_user_date ON daily_report_counts(user_id, date);
CREATE INDEX idx_waitlist_users_email ON waitlist_users(email);

CREATE INDEX idx_ticker_time ON tick_data (ticker, time DESC);
CREATE INDEX idx_time ON tick_data (time);
CREATE INDEX idx_exchange ON tick_data (exchange);
CREATE INDEX idx_sector ON tick_data (sector);

-- Create tick data as a hypertable
SELECT create_hypertable('tick_data', 'time');

-- Create updated_at triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_subscriptions_updated_at
    BEFORE UPDATE ON user_subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_backtest_requests_updated_at
    BEFORE UPDATE ON backtest_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_daily_report_counts_updated_at
    BEFORE UPDATE ON daily_report_counts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column(); 

-- Add Razorpay plan ID to subscription_plans
ALTER TABLE subscription_plans
ADD COLUMN razorpay_plan_id VARCHAR(100) UNIQUE,
ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT true;

-- Add Razorpay subscription fields to user_subscriptions
ALTER TABLE user_subscriptions
ADD COLUMN razorpay_subscription_id VARCHAR(100) UNIQUE,
ADD COLUMN razorpay_payment_id VARCHAR(100),
ADD COLUMN razorpay_signature VARCHAR(255);

-- Add subscription status and is_active
ALTER TABLE user_subscriptions
ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'pending';

-- Add name and picture_url to users
ALTER TABLE users
ADD COLUMN name VARCHAR(255),
ADD COLUMN picture_url VARCHAR(255);

-- Add preview_image_url to backtest_requests
ALTER TABLE backtest_requests
ADD COLUMN preview_image_url VARCHAR(255),
ADD COLUMN is_public BOOLEAN NOT NULL DEFAULT false,
ADD COLUMN share_id VARCHAR(8) UNIQUE;

-- Create indexes for backtest_requests
CREATE INDEX idx_share_id ON backtest_requests(share_id);
