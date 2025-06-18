# Modular Pagination System

This directory contains a modular pagination system that can be reused across different endpoints to avoid code duplication.

## Overview

The `PaginationUtils` class provides generic pagination logic that can be used by any endpoint. Endpoint-specific queries remain in their respective files, while the pagination logic is centralized.

## Components

### PaginationUtils Class

Located in `pagination_utils.py`, this class provides:

- `get_paginated_results()`: Main function for handling standard table-based pagination
- `get_custom_paginated_results()`: Function for complex multi-table queries
- `get_count_query()`: Generates standard count queries for tables
- `get_data_query()`: Generates standard data queries with pagination

### Endpoint Files

Each endpoint file contains:

- Endpoint-specific query functions
- Main endpoint function that uses `PaginationUtils`

## Usage Examples

#### Standard Table Queries (`lagoon_user_txs.py`)

```python
from .pagination_utils import PaginationUtils

def get_user_txs(address: str, offset: int, limit: int, chain_id: int = 480):
    tables_config = {
        "deposit_requests": {
            "owner_join_column": True,
            "count_query": PaginationUtils.get_count_query,
            "data_query": PaginationUtils.get_data_query,
            "query_params": (address, chain_id)
        },
        # ... more tables
    }

    return PaginationUtils.get_paginated_results(
        db=db,
        tables_config=tables_config,
        query_params={},
        offset=offset,
        limit=limit
    )
```

#### Custom Complex Queries (`lagoon_user_position.py`)

```python
# Endpoint-specific queries in the same file
def get_user_position_count_query() -> str:
    return "SELECT COUNT(DISTINCT v.vault_id) AS count FROM vaults v..."

def get_user_position_data_query(offset: int = 0, limit: int = 20) -> str:
    return f"SELECT DISTINCT v.vault_id, v.name as vault_name..."

# Main endpoint function using PaginationUtils
def get_user_position(address: str, offset: int, limit: int, chain_id: int = 480):
    return PaginationUtils.get_custom_paginated_results(
        db=db,
        count_query=get_user_position_count_query,
        data_query=get_user_position_data_query,
        query_params=(address, chain_id, chain_id),
        offset=offset,
        limit=limit,
        result_key="positions"
    )
```

#### Single Table Custom Queries (`lagoon_vault_snapshots.py`)

```python
# Endpoint-specific queries in the same file
def get_vault_snapshots_count_query() -> str:
    return "SELECT COUNT(*) AS count FROM vault_snapshots t..."

def get_vault_snapshots_data_query(offset: int = 0, limit: int = 20) -> str:
    return f"SELECT t.*, v.chain_id, v.name as vault_name..."

# Main endpoint function using PaginationUtils
def get_vault_snapshots(vault_id: str, offset: int, limit: int, chain_id: int = 480):
    return PaginationUtils.get_custom_paginated_results(
        db=db,
        count_query=get_vault_snapshots_count_query,
        data_query=get_vault_snapshots_data_query,
        query_params=(vault_id, chain_id),
        offset=offset,
        limit=limit,
        result_key="snapshots"
    )
```

## Configuration

### Standard Table Configuration

Each table in `tables_config` should have:

- `owner_join_column`: Boolean indicating if the query should join with users table
- `count_query`: Function or string for count query
- `data_query`: Function or string for data query
- `query_params`: Parameters to pass to the queries

### Custom Query Configuration

For complex queries, use:

- `count_query`: SQL query string or callable that returns count query
- `data_query`: SQL query string or callable that returns data query
- `query_params`: Parameters for the queries
- `result_key`: Key name for the results in the response

## Benefits

1. **Code Reuse**: No need to duplicate pagination logic
2. **Consistency**: All endpoints use the same pagination structure
3. **Maintainability**: Changes to pagination logic only need to be made in one place
4. **Flexibility**: Easy to add new endpoints with different table configurations
5. **Separation of Concerns**: Endpoint-specific queries stay with their endpoints
6. **Type Safety**: Proper handling of both simple and complex queries

## Adding New Endpoints

### For Standard Table Queries:

1. Import `PaginationUtils`
2. Define your `tables_config` with the appropriate settings
3. Call `PaginationUtils.get_paginated_results()` with your configuration

### For Custom Complex Queries:

1. Import `PaginationUtils`
2. Create endpoint-specific query functions in your endpoint file
3. Call `PaginationUtils.get_custom_paginated_results()` with your queries
4. Optionally rename the result key to match your API response format

## Architecture Principles

- **PaginationUtils**: Contains only generic pagination logic
- **Endpoint Files**: Contain endpoint-specific queries and business logic
- **Separation**: Queries stay with their endpoints, pagination logic is shared
- **Consistency**: All endpoints use the same pagination structure
