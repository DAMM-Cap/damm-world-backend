-- Lagoon Database Schema

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Custom types & domains
DO $$
BEGIN
  -- Custom enums
  CREATE TYPE deposit_request_status AS ENUM ('pending', 'settled', 'canceled', 'completed');
  CREATE TYPE redeem_request_status AS ENUM ('pending', 'settled', 'completed');
  CREATE TYPE transaction_status AS ENUM ('pending','confirmed','failed','reverted');
  CREATE TYPE vault_status AS ENUM ('open','paused','closing','closed');
  CREATE TYPE event_type AS ENUM (
    'deposit_request','redeem_request','settle_deposit','settle_redeem',
    'deposit','withdraw','transfer','total_assets_updated','deposit_canceled',
    'referral','rates_updated','state_updated','paused','unpaused'
  );
  CREATE TYPE settlement_type AS ENUM ('deposit','redeem');
  CREATE TYPE vault_return_type AS ENUM ('deposit', 'withdraw');
  CREATE TYPE operation_type AS ENUM ('INSERT','UPDATE','DELETE');
  CREATE TYPE network_type AS ENUM ('mainnet','testnet','local');
  CREATE TYPE strategy_type AS ENUM ('yield_farming','staking','lending','custom');

  -- Custom domains
  CREATE DOMAIN bps_type AS INTEGER CHECK (VALUE BETWEEN 0 AND 10000);

EXCEPTION WHEN duplicate_object THEN null;
END
$$;


-- Chains
CREATE TABLE IF NOT EXISTS chains (
  chain_id INTEGER PRIMARY KEY,
  name VARCHAR(50) NOT NULL,
  network_type network_type NOT NULL,
  explorer_url TEXT,
  native_currency_symbol VARCHAR(10),
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

-- Users
CREATE TABLE IF NOT EXISTS users (
  user_id UUID PRIMARY KEY,
  address VARCHAR(42) NOT NULL,
  chain_id INTEGER NOT NULL REFERENCES chains(chain_id),
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  UNIQUE(address, chain_id)
);

-- Tokens
CREATE TABLE IF NOT EXISTS tokens (
  token_id UUID PRIMARY KEY,
  chain_id INTEGER NOT NULL REFERENCES chains(chain_id),
  address VARCHAR(42) NOT NULL,
  symbol VARCHAR(20) NOT NULL,
  name VARCHAR(100) NOT NULL,
  decimals INTEGER NOT NULL,
  created_at TIMESTAMP,
  UNIQUE(chain_id, address)
);

-- Factory
CREATE TABLE IF NOT EXISTS factory (
  chain_id INTEGER NOT NULL,
  genesis_block_number BIGINT NOT NULL,
  vault_address VARCHAR(42) NOT NULL,
  silo_address VARCHAR(42) NOT NULL,
  entrance_rate bps_type,
  exit_rate bps_type,
  continue_indexing BOOLEAN NOT NULL,
  keeper_bot_enabled BOOLEAN NOT NULL,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  PRIMARY KEY(chain_id, vault_address)
);

-- Vaults
CREATE TABLE IF NOT EXISTS vaults (
  vault_id UUID PRIMARY KEY,
  chain_id INTEGER NOT NULL REFERENCES chains(chain_id),
  name VARCHAR(100) NOT NULL,
  vault_token_id UUID NOT NULL REFERENCES tokens(token_id),
  deposit_token_id UUID NOT NULL REFERENCES tokens(token_id),
  strategy_type strategy_type NOT NULL,
  status vault_status NOT NULL,
  total_assets NUMERIC(78,0) NOT NULL, -- Total assets in the vault, updated by NewTotalAssetsUpdated event.
  management_rate bps_type, 
  performance_rate bps_type,
  high_water_mark NUMERIC(78,18), -- Highest price per share reached.
  min_deposit NUMERIC(78,0),
  max_deposit NUMERIC(78,0),
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  administrator_address VARCHAR(42) NOT NULL,
  safe_address VARCHAR(42) NOT NULL,
  price_oracle_address VARCHAR(42) NOT NULL,
  whitelist_manager_address VARCHAR(42) NOT NULL,
  fee_receiver_address VARCHAR(42) NOT NULL,
  fee_registry_address VARCHAR(42) NOT NULL,
  CONSTRAINT valid_deposit_limits CHECK (min_deposit >= 0 AND (max_deposit IS NULL OR max_deposit>min_deposit)),
  UNIQUE(chain_id, vault_token_id)
);

-- Events
CREATE TABLE IF NOT EXISTS events (
  event_id UUID PRIMARY KEY,
  vault_id UUID NOT NULL REFERENCES vaults(vault_id) ON DELETE CASCADE,
  event_type event_type NOT NULL,
  block_number BIGINT NOT NULL,
  log_index INTEGER NOT NULL,
  transaction_hash VARCHAR(66) NOT NULL,
  transaction_status transaction_status,
  event_timestamp TIMESTAMP NOT NULL,
  UNIQUE(vault_id, block_number, log_index)
);

-- Vault Snapshots -- inserts with each update to total assets
CREATE TABLE IF NOT EXISTS vault_snapshots (
  event_id UUID PRIMARY KEY REFERENCES events(event_id) ON DELETE CASCADE,
  vault_id UUID NOT NULL REFERENCES vaults(vault_id) ON DELETE CASCADE,
  total_assets NUMERIC(78,0) NOT NULL,
  total_shares NUMERIC(78,0),
  share_price NUMERIC(78,18),
  management_fee NUMERIC(78,18), -- Regular fee on assets.
  performance_fee NUMERIC(78,18), -- Incentive fee on profits.
  apy NUMERIC(10,6), -- APY in the last delta_hours.
  delta_hours NUMERIC(10,6), -- Variation in hours for determining the apy.
  entrance_rate bps_type, -- Entrance fee rate taken at snapshot time from factory.
  exit_rate bps_type, -- Exit fee rate taken at snapshot time from factory.
  CONSTRAINT positive_values CHECK (total_assets>=0 AND total_shares>=0 AND share_price>=0)
);

-- Deposit Requests
CREATE TABLE IF NOT EXISTS deposit_requests (
  request_id BIGINT,
  event_id UUID PRIMARY KEY REFERENCES events(event_id) ON DELETE CASCADE,
  vault_id UUID NOT NULL REFERENCES vaults(vault_id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(user_id),
  sender_address VARCHAR(42),
  controller_address VARCHAR(42),
  referral_address VARCHAR(42),
  assets NUMERIC(78,0) NOT NULL,
  status deposit_request_status NOT NULL,
  updated_at TIMESTAMP,
  settled_at TIMESTAMP,
  CONSTRAINT positive_assets CHECK (assets>0)
);

-- Redeem Requests
CREATE TABLE IF NOT EXISTS redeem_requests (
  request_id BIGINT,
  event_id UUID NOT NULL PRIMARY KEY REFERENCES events(event_id) ON DELETE CASCADE,
  vault_id UUID NOT NULL REFERENCES vaults(vault_id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(user_id),
  sender_address VARCHAR(42),
  controller_address VARCHAR(42),
  shares NUMERIC(78,0) NOT NULL,
  status redeem_request_status NOT NULL,
  updated_at TIMESTAMP,
  settled_at TIMESTAMP,
  CONSTRAINT positive_shares CHECK (shares>0)
);

-- Settlements
CREATE TABLE IF NOT EXISTS settlements (
  event_id UUID NOT NULL PRIMARY KEY REFERENCES events(event_id) ON DELETE CASCADE,
  vault_id UUID NOT NULL REFERENCES vaults(vault_id) ON DELETE CASCADE,
  settlement_type settlement_type NOT NULL,
  epoch_id BIGINT
);

-- Transfers
CREATE TABLE IF NOT EXISTS transfers (
  event_id UUID PRIMARY KEY REFERENCES events(event_id) ON DELETE CASCADE,
  vault_id UUID NOT NULL REFERENCES vaults(vault_id) ON DELETE CASCADE,
  from_address VARCHAR(42),
  to_address VARCHAR(42),
  amount NUMERIC(78,0) NOT NULL,
  CONSTRAINT positive_amount CHECK (amount>=0),
  CONSTRAINT valid_transfer_addresses CHECK (from_address IS NOT NULL OR to_address IS NOT NULL)
);

-- Returns
-- When return type is deposit, assets is the amount of assets deposited and shares is the amount of shares minted.
-- When return type is withdrawal, assets is the amount of assets withdrawn and shares is the amount of shares burned.
CREATE TABLE IF NOT EXISTS vault_returns (
  event_id UUID PRIMARY KEY REFERENCES events(event_id) ON DELETE CASCADE,
  vault_id UUID NOT NULL REFERENCES vaults(vault_id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(user_id),
  return_type vault_return_type NOT NULL,
  assets NUMERIC(78,0) NOT NULL,
  shares NUMERIC(78,0) NOT NULL,
  CONSTRAINT positive_return CHECK (assets > 0 AND shares > 0)
);

-- User Positions
CREATE TABLE IF NOT EXISTS user_positions (
  vault_id UUID NOT NULL REFERENCES vaults(vault_id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(user_id),
  shares_balance NUMERIC(78,0),
  assets_value NUMERIC(78,0),
  total_deposited NUMERIC(78,0),
  total_withdrawn NUMERIC(78,0),
  first_deposit_at TIMESTAMP,
  updated_at TIMESTAMP,
  PRIMARY KEY (vault_id, user_id),
  CONSTRAINT non_negative_balance CHECK (shares_balance>=0 AND assets_value>=0)
);

-- Indexer State
CREATE TABLE IF NOT EXISTS indexer_state (
  vault_id UUID PRIMARY KEY REFERENCES vaults(vault_id) ON DELETE CASCADE,
  last_processed_block BIGINT,
  last_processed_timestamp TIMESTAMP,
  indexer_version VARCHAR(20),
  is_syncing BOOLEAN,
  sync_started_at TIMESTAMP,
  updated_at TIMESTAMP
);

-- Bot Status
CREATE TABLE IF NOT EXISTS bot_status (
  vault_id UUID PRIMARY KEY REFERENCES vaults(vault_id) ON DELETE CASCADE,
  last_processed_block BIGINT,
  last_processed_timestamp TIMESTAMP,
  in_sync BOOLEAN,
  updated_at TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_vaults_chain_status ON vaults(chain_id, status);
CREATE INDEX IF NOT EXISTS idx_events_vault_type_time ON events(vault_id, event_type, event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_deposit_requests_user_status ON deposit_requests(user_id, status);
CREATE INDEX IF NOT EXISTS idx_deposit_requests_vault_status ON deposit_requests(vault_id, status);
CREATE INDEX IF NOT EXISTS idx_redeem_requests_user_status ON redeem_requests(user_id, status);
CREATE INDEX IF NOT EXISTS idx_redeem_requests_vault_status ON redeem_requests(vault_id, status);
CREATE INDEX IF NOT EXISTS idx_transfers_from_to ON transfers(from_address, to_address);
CREATE INDEX IF NOT EXISTS idx_user_positions_user ON user_positions(user_id);
CREATE INDEX IF NOT EXISTS idx_indexer_vault ON indexer_state(vault_id);
CREATE INDEX IF NOT EXISTS idx_indexer_is_syncing ON indexer_state(is_syncing);
CREATE INDEX IF NOT EXISTS idx_indexer_last_processed_time ON indexer_state(last_processed_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_bot_status_vault ON bot_status(vault_id);
CREATE INDEX IF NOT EXISTS idx_bot_status_in_sync ON bot_status(in_sync);
CREATE INDEX IF NOT EXISTS idx_bot_status_last_processed_time ON bot_status(last_processed_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_txhash ON events(transaction_hash);
CREATE INDEX IF NOT EXISTS idx_user_positions_vault_user ON user_positions(vault_id, user_id);
CREATE INDEX IF NOT EXISTS idx_vault_snapshots_vault_id ON vault_snapshots(vault_id);
CREATE INDEX IF NOT EXISTS idx_vaults_id ON vaults(vault_id);
CREATE INDEX IF NOT EXISTS idx_settlements_type_epoch ON settlements(settlement_type, epoch_id);
CREATE INDEX IF NOT EXISTS idx_vaults_vault_token_id ON vaults(vault_token_id);
CREATE INDEX IF NOT EXISTS idx_tokens_address_chain_id ON tokens(address, chain_id);
CREATE INDEX IF NOT EXISTS idx_factory_vault_address_chain_id ON factory(vault_address, chain_id);
