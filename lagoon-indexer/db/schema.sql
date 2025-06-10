-- Lagoon Database Schema

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enums
DO $$
BEGIN
  CREATE TYPE deposit_request_status AS ENUM ('pending', 'settled', 'canceled', 'completed');
  CREATE TYPE redeem_request_status AS ENUM ('pending', 'settled', 'completed');
  CREATE TYPE transaction_status AS ENUM ('pending','confirmed','failed','reverted');
  CREATE TYPE vault_status AS ENUM ('active','paused','closed');
  CREATE TYPE event_type AS ENUM (
    'deposit_request','redeem_request','settle_deposit','settle_redeem',
    'deposit','withdraw','transfer','total_assets_updated','deposit_canceled'
  );
  CREATE TYPE settlement_type AS ENUM ('deposit','redeem');
  CREATE TYPE transfer_type AS ENUM ('standard','mint','burn');
  CREATE TYPE operation_type AS ENUM ('INSERT','UPDATE','DELETE');
  CREATE TYPE network_type AS ENUM ('mainnet','testnet','local');
  CREATE TYPE strategy_type AS ENUM ('yield_farming','staking','lending','custom');
EXCEPTION WHEN duplicate_object THEN null;
END
$$;


-- Users
CREATE TABLE IF NOT EXISTS users (
  user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  address VARCHAR(42) UNIQUE NOT NULL,
  display_name VARCHAR(100),
  email VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Chains
CREATE TABLE IF NOT EXISTS chains (
  chain_id INTEGER PRIMARY KEY,
  name VARCHAR(50) NOT NULL,
  network_type network_type NOT NULL DEFAULT 'mainnet',
  rpc_url TEXT,
  explorer_url TEXT,
  native_currency_symbol VARCHAR(10),
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE chains ENABLE ROW LEVEL SECURITY;

-- Tokens
CREATE TABLE IF NOT EXISTS tokens (
  token_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  chain_id INTEGER NOT NULL REFERENCES chains(chain_id),
  address VARCHAR(42) NOT NULL,
  symbol VARCHAR(20) NOT NULL,
  name VARCHAR(100) NOT NULL,
  decimals INTEGER NOT NULL DEFAULT 18,
  is_native BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(chain_id, address)
);
ALTER TABLE tokens ENABLE ROW LEVEL SECURITY;

-- Vaults
CREATE TABLE IF NOT EXISTS vaults (
  vault_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  chain_id INTEGER NOT NULL REFERENCES chains(chain_id),
  name VARCHAR(100) NOT NULL,
  description TEXT,
  vault_token_id UUID NOT NULL REFERENCES tokens(token_id),
  deposit_token_id UUID NOT NULL REFERENCES tokens(token_id),
  strategy_type strategy_type NOT NULL DEFAULT 'yield_farming',
  status vault_status NOT NULL DEFAULT 'active',
  fee_percentage NUMERIC(5,4) DEFAULT 0.0000,
  performance_fee_percentage NUMERIC(5,4) DEFAULT 0.0000,
  min_deposit NUMERIC(78,0) DEFAULT 0,
  max_deposit NUMERIC(78,0),
  total_value_locked NUMERIC(78,0) DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT positive_fees CHECK (fee_percentage>=0 AND performance_fee_percentage>=0),
  CONSTRAINT valid_deposit_limits CHECK (min_deposit >= 0 AND (max_deposit IS NULL OR max_deposit>min_deposit))
);
ALTER TABLE vaults ENABLE ROW LEVEL SECURITY;

-- Vault Snapshots (partitioned)
CREATE TABLE IF NOT EXISTS vault_snapshots (
  snapshot_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  vault_id UUID NOT NULL REFERENCES vaults(vault_id) ON DELETE CASCADE,
  nav NUMERIC(78,18) NOT NULL,
  total_assets NUMERIC(78,0) NOT NULL,
  total_shares NUMERIC(78,0) NOT NULL,
  share_price NUMERIC(78,18) NOT NULL,
  apy NUMERIC(10,6),
  main_token_balance NUMERIC(78,0),
  secondary_token_balance NUMERIC(78,0),
  recorded_at TIMESTAMP NOT NULL,
  block_number BIGINT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT positive_values CHECK (nav>0 AND total_assets>=0 AND total_shares>=0 AND share_price>0)
) PARTITION BY RANGE(recorded_at);
ALTER TABLE vault_snapshots ENABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS vault_snapshots_2025_06 PARTITION OF vault_snapshots
  FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');

-- Events (partitioned)
CREATE TABLE IF NOT EXISTS events (
  event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  vault_id UUID NOT NULL REFERENCES vaults(vault_id) ON DELETE CASCADE,
  event_type event_type NOT NULL,
  block_number BIGINT NOT NULL,
  log_index INTEGER NOT NULL,
  transaction_hash VARCHAR(66) NOT NULL,
  transaction_status transaction_status DEFAULT 'confirmed',
  gas_used BIGINT,
  gas_price BIGINT,
  event_timestamp TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(vault_id, block_number, log_index)
) PARTITION BY RANGE(event_timestamp);
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- Deposit Requests
CREATE TABLE IF NOT EXISTS deposit_requests (
  request_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  event_id UUID NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
  vault_id UUID NOT NULL REFERENCES vaults(vault_id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(user_id),
  controller_address VARCHAR(42),
  sender_address VARCHAR(42),
  assets NUMERIC(78,0) NOT NULL,
  status deposit_request_status NOT NULL DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  settled_at TIMESTAMP,
  CONSTRAINT positive_assets CHECK (assets>0)
);
ALTER TABLE deposit_requests ENABLE ROW LEVEL SECURITY;

-- Redeem Requests
CREATE TABLE IF NOT EXISTS redeem_requests (
  request_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  event_id UUID NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
  vault_id UUID NOT NULL REFERENCES vaults(vault_id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(user_id),
  controller_address VARCHAR(42),
  sender_address VARCHAR(42),
  shares NUMERIC(78,0) NOT NULL,
  status redeem_request_status NOT NULL DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  settled_at TIMESTAMP,
  CONSTRAINT positive_shares CHECK (shares>0)
);
ALTER TABLE redeem_requests ENABLE ROW LEVEL SECURITY;

-- Settlements
CREATE TABLE IF NOT EXISTS settlements (
  settlement_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  event_id UUID NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
  vault_id UUID NOT NULL REFERENCES vaults(vault_id) ON DELETE CASCADE,
  settlement_type settlement_type NOT NULL,
  epoch_id BIGINT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE settlements ENABLE ROW LEVEL SECURITY;

-- Transfers
CREATE TABLE IF NOT EXISTS transfers (
  transfer_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  event_id UUID NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
  vault_id UUID NOT NULL REFERENCES vaults(vault_id) ON DELETE CASCADE,
  from_address VARCHAR(42),
  to_address VARCHAR(42),
  value NUMERIC(78,0) NOT NULL,
  transfer_type transfer_type DEFAULT 'standard',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT positive_value CHECK (value>=0),
  CONSTRAINT valid_transfer_addresses CHECK (from_address IS NOT NULL OR to_address IS NOT NULL)
);
ALTER TABLE transfers ENABLE ROW LEVEL SECURITY;

-- Withdrawals
CREATE TABLE IF NOT EXISTS withdrawals (
  withdrawal_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  event_id UUID NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
  vault_id UUID NOT NULL REFERENCES vaults(vault_id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(user_id),
  receiver_address VARCHAR(42),
  sender_address VARCHAR(42),
  assets_withdrawn NUMERIC(78,0) NOT NULL,
  shares_burned NUMERIC(78,0) NOT NULL,
  withdrawal_fee NUMERIC(78,0) DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT positive_withdrawal CHECK (assets_withdrawn>0 AND shares_burned>0)
);
ALTER TABLE withdrawals ENABLE ROW LEVEL SECURITY;

-- User Positions
CREATE TABLE IF NOT EXISTS user_positions (
  position_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  vault_id UUID NOT NULL REFERENCES vaults(vault_id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(user_id),
  shares_balance NUMERIC(78,0) DEFAULT 0,
  assets_value NUMERIC(78,0) DEFAULT 0,
  average_entry_price NUMERIC(78,18) DEFAULT 0,
  total_deposited NUMERIC(78,0) DEFAULT 0,
  total_withdrawn NUMERIC(78,0) DEFAULT 0,
  realized_pnl NUMERIC(78,0) DEFAULT 0,
  unrealized_pnl NUMERIC(78,0) DEFAULT 0,
  first_deposit_at TIMESTAMP,
  last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(vault_id,user_id),
  CONSTRAINT non_negative_balance CHECK (shares_balance>=0 AND assets_value>=0)
);
ALTER TABLE user_positions ENABLE ROW LEVEL SECURITY;

-- Indexer State
CREATE TABLE IF NOT EXISTS indexer_state (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  vault_id UUID NOT NULL REFERENCES vaults(vault_id) ON DELETE CASCADE,
  chain_id INTEGER NOT NULL REFERENCES chains(chain_id),
  last_processed_block BIGINT NOT NULL,
  last_processed_timestamp TIMESTAMP,
  indexer_version VARCHAR(20) DEFAULT '1.0.0',
  is_syncing BOOLEAN DEFAULT false,
  sync_started_at TIMESTAMP,
  error_count INTEGER DEFAULT 0,
  last_error TEXT,
  last_error_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(vault_id,chain_id)
);
ALTER TABLE indexer_state ENABLE ROW LEVEL SECURITY;

-- Audit Log
CREATE TABLE IF NOT EXISTS audit_log (
  audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  table_name VARCHAR(50) NOT NULL,
  record_id UUID,
  operation operation_type,
  old_values JSONB,
  new_values JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY users_select_self ON users FOR SELECT USING (user_id::text = current_setting('myapp.current_user_id', true));
CREATE POLICY users_update_self ON users FOR UPDATE USING (user_id::text = current_setting('myapp.current_user_id', true));

CREATE POLICY deposits_select_own ON deposit_requests FOR SELECT USING (user_id::text = current_setting('myapp.current_user_id', true));
CREATE POLICY deposits_update_own ON deposit_requests FOR UPDATE USING (user_id::text = current_setting('myapp.current_user_id', true));

CREATE POLICY redeemrequests_select_own ON redeem_requests FOR SELECT USING (user_id::text = current_setting('myapp.current_user_id', true));
CREATE POLICY redeemrequests_update_own ON redeem_requests FOR UPDATE USING (user_id::text = current_setting('myapp.current_user_id', true));

CREATE POLICY withdrawals_select_own ON withdrawals FOR SELECT USING (user_id::text = current_setting('myapp.current_user_id', true));
CREATE POLICY withdrawals_update_own ON withdrawals FOR UPDATE USING (user_id::text = current_setting('myapp.current_user_id', true));

CREATE POLICY positions_select_own ON user_positions FOR SELECT USING (user_id::text = current_setting('myapp.current_user_id', true));
CREATE POLICY positions_update_own ON user_positions FOR UPDATE USING (user_id::text = current_setting('myapp.current_user_id', true));

CREATE POLICY vaultsnapshots_select ON vault_snapshots FOR SELECT USING (true);
CREATE POLICY events_select ON events FOR SELECT USING (true);

-- Public Selects Blocking for admin/internal
CREATE POLICY indexer_no_access ON indexer_state FOR SELECT USING (false);
CREATE POLICY auditlog_no_access ON audit_log FOR SELECT USING (false);

-- Views
CREATE OR REPLACE VIEW user_events_view AS
WITH user_address AS (
  SELECT current_setting('myapp.current_user_address', true) AS address
)
SELECT
  'deposit_request' AS event_type,
  dr.request_id AS event_id,
  dr.vault_id,
  dr.user_id,
  dr.assets AS amount,
  dr.status,
  e.transaction_hash,
  e.event_timestamp AS timestamp
FROM deposit_requests dr
JOIN events e ON dr.event_id = e.event_id
JOIN user_address ua ON dr.sender_address = ua.address

UNION ALL

SELECT
  'redeem_request' AS event_type,
  rr.request_id AS event_id,
  rr.vault_id,
  rr.user_id,
  rr.shares AS amount,
  rr.status,
  e.transaction_hash,
  e.event_timestamp AS timestamp
FROM redeem_requests rr
JOIN events e ON rr.event_id = e.event_id
JOIN user_address ua ON rr.sender_address = ua.address

UNION ALL

SELECT
  'withdraw' AS event_type,
  w.withdrawal_id AS event_id,
  w.vault_id,
  w.user_id,
  w.assets_withdrawn AS amount,
  'completed' AS status,
  e.transaction_hash,
  e.event_timestamp AS timestamp
FROM withdrawals w
JOIN events e ON w.event_id = e.event_id
JOIN user_address ua ON w.receiver_address = ua.address

UNION ALL

SELECT
  'transfer' AS event_type,
  t.transfer_id AS event_id,
  t.vault_id,
  NULL AS user_id,
  t.value AS amount,
  'confirmed' AS status,
  e.transaction_hash,
  e.event_timestamp AS timestamp
FROM transfers t
JOIN events e ON t.event_id = e.event_id
JOIN user_address ua
  ON t.from_address = ua.address
  OR t.to_address = ua.address;

CREATE OR REPLACE VIEW vault_total_assets_updates_view AS
SELECT
  e.event_id,
  e.vault_id,
  vs.total_assets,
  e.block_number,
  e.log_index,
  e.transaction_hash,
  e.event_timestamp
FROM events e
JOIN vault_snapshots vs ON e.vault_id = vs.vault_id
WHERE e.event_type = 'total_assets_updated';

CREATE OR REPLACE VIEW vault_performance AS
  SELECT v.vault_id, v.name, v.chain_id,
    vs.nav, vs.total_assets, vs.total_shares, vs.share_price, vs.apy, vs.recorded_at,
    LAG(vs.share_price) OVER (PARTITION BY v.vault_id ORDER BY vs.recorded_at) AS prev_share_price,
    (vs.share_price / NULLIF(LAG(vs.share_price) OVER (PARTITION BY v.vault_id ORDER BY vs.recorded_at),0) - 1) * 100 AS price_change_pct
  FROM vaults v
  JOIN vault_snapshots vs USING (vault_id)
  WHERE v.status = 'active';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_vaults_chain_status ON vaults(chain_id, status);
CREATE INDEX IF NOT EXISTS idx_events_vault_type_time ON events(vault_id, event_type, event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_deposit_requests_user_status ON deposit_requests(user_id, status);
CREATE INDEX IF NOT EXISTS idx_deposit_requests_vault_status ON deposit_requests(vault_id, status);
CREATE INDEX IF NOT EXISTS idx_redeem_requests_user_status ON redeem_requests(user_id, status);
CREATE INDEX IF NOT EXISTS idx_redeem_requests_vault_status ON redeem_requests(vault_id, status);
CREATE INDEX IF NOT EXISTS idx_transfers_from_to ON transfers(from_address, to_address);
CREATE INDEX IF NOT EXISTS idx_user_positions_user ON user_positions(user_id);
CREATE INDEX IF NOT EXISTS idx_indexer_vault_chain ON indexer_state(vault_id, chain_id);
CREATE INDEX IF NOT EXISTS idx_indexer_is_syncing ON indexer_state(is_syncing);
CREATE INDEX IF NOT EXISTS idx_indexer_last_processed_time ON indexer_state(last_processed_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_txhash ON events(transaction_hash);
CREATE INDEX IF NOT EXISTS idx_user_positions_vault_user ON user_positions(vault_id, user_id);
CREATE INDEX IF NOT EXISTS idx_vault_snapshots_recorded_at ON vault_snapshots(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_vaults_id ON vaults(vault_id);
CREATE INDEX IF NOT EXISTS idx_settlements_type_epoch ON settlements(settlement_type, epoch_id);


-- Triggers: update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column() RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_tokens_updated_at BEFORE UPDATE ON tokens FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_chains_updated_at BEFORE UPDATE ON chains FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_vaults_updated_at BEFORE UPDATE ON vaults FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_deposit_requests_updated_at BEFORE UPDATE ON deposit_requests FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_redeem_requests_updated_at BEFORE UPDATE ON redeem_requests FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_positions_updated_at BEFORE UPDATE ON user_positions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_indexer_state_updated_at BEFORE UPDATE ON indexer_state FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Audit Logging
CREATE OR REPLACE FUNCTION audit_trigger_function() RETURNS TRIGGER AS $$
DECLARE
  old_data JSONB;
  new_data JSONB;
  record_id UUID;
BEGIN
  -- Dynamically determine the primary key based on the table name (convention: {table}_id)
  record_id := COALESCE(
    (OLD.*)::jsonb ->> (TG_TABLE_NAME || '_id'),
    (NEW.*)::jsonb ->> (TG_TABLE_NAME || '_id'),
    (OLD.*)::jsonb ->> 'vault_id',  -- fallback for tables without PK following naming convention
    (NEW.*)::jsonb ->> 'vault_id'
  )::uuid;

  IF TG_OP = 'DELETE' THEN
    old_data := to_jsonb(OLD);
    INSERT INTO audit_log(table_name, record_id, operation, old_values)
    VALUES (TG_TABLE_NAME, record_id, TG_OP::operation_type, old_data);
    RETURN OLD;

  ELSIF TG_OP = 'UPDATE' THEN
    old_data := to_jsonb(OLD);
    new_data := to_jsonb(NEW);
    INSERT INTO audit_log(table_name, record_id, operation, old_values, new_values)
    VALUES (TG_TABLE_NAME, record_id, TG_OP::operation_type, old_data, new_data);
    RETURN NEW;

  ELSIF TG_OP = 'INSERT' THEN
    new_data := to_jsonb(NEW);
    INSERT INTO audit_log(table_name, record_id, operation, new_values)
    VALUES (TG_TABLE_NAME, record_id, TG_OP::operation_type, new_data);
    RETURN NEW;
  END IF;

  RETURN NULL;
END;
$$ LANGUAGE plpgsql;


-- Attach audit triggers
CREATE TRIGGER audit_vaults_trigger
  AFTER INSERT OR UPDATE OR DELETE ON vaults
  FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER audit_deposit_requests_trigger
  AFTER INSERT OR UPDATE OR DELETE ON deposit_requests
  FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER audit_redeem_requests_trigger
  AFTER INSERT OR UPDATE OR DELETE ON redeem_requests
  FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER audit_withdrawals_trigger
  AFTER INSERT OR UPDATE OR DELETE ON withdrawals
  FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER audit_user_positions_trigger
  AFTER INSERT OR UPDATE OR DELETE ON user_positions
  FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER audit_transfers_trigger
  AFTER INSERT OR UPDATE OR DELETE ON transfers
  FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER audit_indexer_state_trigger
  AFTER INSERT OR UPDATE OR DELETE ON indexer_state
  FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER audit_settlements_trigger
  AFTER INSERT OR UPDATE OR DELETE ON settlements
  FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();
