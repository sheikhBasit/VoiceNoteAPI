-- Create Wallets Table
CREATE TABLE IF NOT EXISTS wallets (
    user_id VARCHAR PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    balance INTEGER DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'USD',
    is_frozen BOOLEAN DEFAULT FALSE,
    stripe_customer_id VARCHAR,
    stripe_subscription_id VARCHAR,
    auto_recharge_enabled BOOLEAN DEFAULT FALSE,
    recharge_threshold INTEGER DEFAULT 500,
    recharge_amount INTEGER DEFAULT 2000,
    updated_at BIGINT
);

CREATE INDEX IF NOT EXISTS ix_wallets_stripe_customer_id ON wallets(stripe_customer_id);

-- Create Transactions Table
CREATE TABLE IF NOT EXISTS transactions (
    id VARCHAR PRIMARY KEY,
    wallet_id VARCHAR REFERENCES wallets(user_id),
    amount INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    type VARCHAR(20) NOT NULL,
    description VARCHAR,
    reference_id VARCHAR,
    created_at BIGINT
);

CREATE INDEX IF NOT EXISTS ix_transactions_wallet_id ON transactions(wallet_id);

-- Create UsageLogs Table
CREATE TABLE IF NOT EXISTS usage_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR REFERENCES users(id),
    endpoint VARCHAR,
    duration_seconds INTEGER DEFAULT 0,
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    provider VARCHAR,
    model VARCHAR,
    cost_estimated INTEGER DEFAULT 0,
    status INTEGER DEFAULT 200,
    timestamp BIGINT
);

CREATE INDEX IF NOT EXISTS ix_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX IF NOT EXISTS ix_usage_logs_endpoint ON usage_logs(endpoint);

-- Initialize Wallets for existing users
INSERT INTO wallets (user_id, balance, updated_at)
SELECT id, 100, EXTRACT(EPOCH FROM NOW()) * 1000
FROM users
WHERE id NOT IN (SELECT user_id FROM wallets);
