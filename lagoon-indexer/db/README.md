# Lagoon Database Schema

This directory contains the PostgreSQL schema for the **Lagoon Indexer**, a backend component for tracking DeFi vault activity across supported chains.

## 📦 Schema Overview

The schema captures all key lifecycle events and performance metrics related to Lagoon vaults, including deposits, redemptions, transfers, fees, and APY tracking.

### 🧩 Core Tables

- **`users`**: Registered user addresses per chain
- **`chains`**: Supported networks and metadata
- **`tokens`**: Token metadata per chain
- **`vaults`**: Configuration and live state of each vault, including:
  - `total_assets`
  - `management_rate`, `performance_rate` (in BPS)
  - `high_water_mark` (max historical share price)
  - deposit constraints and administrator addresses

### 🔁 Event & Transaction Tables

- **`events`**: Canonical source of all on-chain event data. Event types include:
  - `deposit_request`
  - `redeem_request`
  - `settle_deposit`
  - `settle_redeem`
  - `deposit`
  - `withdraw`
  - `transfer`
  - `total_assets_updated`
  - `rates_updated`
  - `referral`
  - `deposit_canceled`
- **`deposit_requests`**: Records deposit intents and status
- **`redeem_requests`**: Records redemption intents and status
- **`settlements`**: Tracks epoch-based deposit/redeem settlements
- **`vault_returns`**: Records actual deposits and withdrawals
- **`transfers`**: Logs share or asset transfers between users

### 📈 State Tracking Tables

- **`vault_snapshots`**: Periodic metrics for vaults including:
  - `share_price`
  - `management_fee` and `performance_fee`
  - `apy` and `delta_hours` (time window of APY calc)
- **`user_positions`**: Tracks user shares, asset value, and activity
- **`indexer_state`**: Keeps track of indexer progress per vault/chain

## ⚙️ Features

- ✅ Uses UUIDs for consistent record identity
- ✅ Rich enum types for transaction and status classification
- ✅ BPS-based fee modeling (`bps_type`)
- ✅ Auto-updated `updated_at` columns via PostgreSQL triggers
- ✅ Foreign key constraints for data integrity
- ✅ Full indexing for efficient event and state queries

## 📐 Schema Diagram

![Lagoon Database Schema](Lagoon%20DB%20Schema.png)

## 📄 Implementation Details

The schema is defined in `schema.sql` and includes:

- `CREATE TYPE` definitions for enum-based modeling of states
- `CREATE DOMAIN` for BPS validation (0–10000)
- Referential constraints to ensure consistency across tables
- `vault_snapshots` designed to compute and store APY, fees, and share price dynamics
- Triggers for consistent `updated_at` tracking
- Indexed fields on all frequent query columns
