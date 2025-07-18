# Lagoon Database Schema

This directory contains the PostgreSQL schema for the **Lagoon Indexer**, a backend component for tracking DeFi vault activity across supported chains.

## 📦 Schema Overview

The schema captures all key lifecycle events and performance metrics related to Lagoon vaults, including deposits, redemptions, transfers, fees, APY tracking, and real-time indexing metadata.

### 🧩 Core Tables

- **`chains`**: Supported blockchain networks with metadata such as name, type (`mainnet`, `testnet`, `local`), and explorer URLs.
- **`users`**: Registered user addresses per chain.
- **`tokens`**: ERC-20 or wrapped native token metadata per chain.
- **`factory`**: Tracks initial vault and silo deployments per chain. Used for bootstrapping new indexers.
- **`vaults`**: Configuration and state of each vault, including:
  - Token associations
  - Fee configurations (`management_rate`, `performance_rate`)
  - High-water marks and APY details
  - Deposit limits and administrator contract addresses

### 🔁 Event & Transaction Tables

- **`events`**: Canonical source of all indexed on-chain events. Event types include:
  - `deposit_request`, `redeem_request`
  - `settle_deposit`, `settle_redeem`
  - `deposit`, `withdraw`, `transfer`
  - `total_assets_updated`, `rates_updated`, `referral`
  - `state_updated`, `paused`, `unpaused`, `deposit_canceled`
- **`deposit_requests`**: User-initiated deposit intents with status tracking (`pending`, `settled`, `canceled`, `completed`).
- **`redeem_requests`**: User-initiated redemption intents with similar status tracking.
- **`settlements`**: Epoch-based matching of deposits and redemptions into vault operations.
- **`vault_returns`**: Records actual deposits and withdrawals by users, including asset and share amounts.
- **`transfers`**: Logs movement of shares or tokens between user addresses.

### 📈 State Tracking Tables

- **`vault_snapshots`**: Tracks periodic updates to total assets, share price, APY, and associated fees.
- **`user_positions`**: Maintains user-level balances and cumulative activity (deposited, withdrawn, current asset value).
- **`indexer_state`**: Tracks indexer progress on a per-vault basis, including last processed block, timestamps, and syncing status.
- **`bot_status`**: Tracks the status of off-chain bots that perform automated operations per vault.

### 🗃️ Data Integrity and Optimization

- ✅ Uses UUIDs for consistent identity across events, users, and vaults
- ✅ Rich enum types for classification of request, transaction, and strategy types
- ✅ BPS-based domain (`bps_type`) to model fees safely
- ✅ Foreign key constraints for relational integrity
- ✅ Conditional constraints for deposit limits and positive values
- ✅ Indexed fields on all high-frequency access paths

### 🧪 Enum Types

- `vault_status`: `open`, `paused`, `closing`, `closed`
- `deposit_request_status`: `pending`, `settled`, `canceled`, `completed`
- `redeem_request_status`: `pending`, `settled`, `completed`
- `transaction_status`: `pending`, `confirmed`, `failed`, `reverted`
- `event_type`: Captures all supported on-chain event kinds
- `settlement_type`: `deposit`, `redeem`
- `vault_return_type`: `deposit`, `withdraw`
- `operation_type`: `INSERT`, `UPDATE`, `DELETE`
- `network_type`: `mainnet`, `testnet`, `local`
- `strategy_type`: `yield_farming`, `staking`, `lending`, `custom`

## 📐 Schema Diagram

![Lagoon Database Schema](Lagoon%20DB%20Schema.png)

## 📄 Implementation Details

The schema is defined in `schema.sql` and includes:

- `CREATE TYPE` definitions for enum-based modeling of states
- `CREATE DOMAIN` definitions for safe BPS handling
- Referential integrity via `FOREIGN KEY` constraints
- `CHECK` constraints for data validity (e.g. non-negative balances, valid limits)
- `ON DELETE CASCADE` for relevant foreign keys (e.g. `events`)
- Strategic indexes to support high-performance queries for:
  - User positions
  - Vault snapshots
  - Event histories
  - Sync and bot status tables

## 🧰 Used In

- `run_schema.py`: Initializes the schema and inserts chain/token metadata
- `insert_factory_data.py`: Derives factory deployments from on-chain creation txs
- `lagoon_indexer.py`: Real-time vault indexer triggered per vault deployment
- `keeper bots`: Off-chain automation agents that consume sync state
