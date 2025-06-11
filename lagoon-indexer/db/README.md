# Lagoon Database Schema

This directory contains the database schema for the Lagoon indexer, which tracks DeFi vault operations and user interactions.

## Schema Overview

The database is designed to track all operations related to Lagoon vaults, including deposits, withdrawals, transfers, and user positions. Here's a high-level overview of the main components:

### Core Tables

- `users`: Stores user addresses
- `chains`: Tracks supported blockchain networks
- `tokens`: Manages token information (addresses, symbols, decimals)
- `vaults`: Main vault configurations with fees, limits, and addresses

### Transaction Tables

- `events`: Base table for all blockchain events
- `deposit_requests`: Tracks deposit operations
- `redeem_requests`: Tracks redemption operations
- `transfers`: Records token transfers
- `withdrawals`: Manages withdrawal operations
- `settlements`: Tracks settlement events

### State Tables

- `vault_snapshots`: Records vault performance metrics
- `user_positions`: Tracks user balances and PnL
- `indexer_state`: Monitors blockchain indexing progress

## Key Features

- Uses UUIDs for primary keys
- Implements custom enums for statuses and types
- Includes comprehensive indexing for performance
- Has triggers for automatic timestamp updates
- Enforces data integrity with constraints

## Schema Diagram

![Lagoon Database Schema](Lagoon%20DB%20Schema.png)

## Implementation Details

The schema is implemented in `schema.sql` and includes:

- Custom types and domains for data validation
- Foreign key relationships for referential integrity
- Indexes for query optimization
- Triggers for automatic timestamp updates
- Constraints for data validation

For detailed implementation, refer to the `schema.sql` file in this directory.
