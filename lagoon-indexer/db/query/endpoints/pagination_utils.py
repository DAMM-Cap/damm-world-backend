from typing import Dict, Any, List, Callable, Tuple, Union
from db.db import Database
from utils.converters import convert_numpy_types

class PaginationUtils:
    @staticmethod
    def get_paginated_results(
        db: Database,
        tables_config: Dict[str, Dict[str, Any]],
        count_query_params: Dict[str, Any],
        data_query_params: Dict[str, Any],
        offset: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Generic pagination function that can be used for any endpoint.
        
        Args:
            db: Database connection
            tables_config: Dictionary with table configurations
                {
                    "table_name": {
                        "owner_join_column": bool,
                        "count_query": str or Callable,
                        "data_query": str or Callable,
                        "query_params": Dict[str, Any]
                    }
                }
            count_query_params: Common parameters for all count queries
            data_query_params: Common parameters for all data queries
            offset: Pagination offset
            limit: Number of items per page
            
        Returns:
            Dictionary with total count, next_offset, and results
        """
        total_count = 0
        all_results = []

        for table_name, config in tables_config.items():
            # Get count
            count_query = config["count_query"]
            if callable(count_query):
                count_query = count_query(table_name, config["owner_join_column"])
            
            count_params = config["count_query_params"]
            count_df = db.frameResponse(count_query, count_params)
            
            if not count_df.empty:
                total_count += int(count_df.iloc[0]['count'])

            # Get data
            data_query = config["data_query"]
            if callable(data_query):
                data_query = data_query(table_name, config["owner_join_column"], offset, limit)
            
            data_params = config["data_query_params"]
            data_df = db.frameResponse(data_query, data_params)
            
            if not data_df.empty:
                results = data_df.to_dict(orient="records")
                results_converted = [convert_numpy_types(r) for r in results]
                all_results.extend(results_converted)

        # Sort combined results
        all_results_sorted = sorted(
            all_results,
            key=lambda x: (x.get('block_number', 0), x.get('log_index', 0)),
            reverse=True
        )

        return {
            "total": total_count,
            "next_offset": offset + limit if offset + limit < total_count else None,
            "results": all_results_sorted
        }

    @staticmethod
    def get_custom_paginated_results(
        db: Database,
        count_query: Union[str, Callable],
        data_query: Union[str, Callable],
        count_query_params: Tuple,
        data_query_params: Tuple,
        offset: int = 0,
        limit: int = 20,
        result_key: str = "results"
    ) -> Dict[str, Any]:
        """
        Custom pagination function for complex queries that don't fit the standard table pattern.
        
        Args:
            db: Database connection
            count_query: SQL query string or callable that returns count query
            data_query: SQL query string or callable that returns data query
            count_query_params: Parameters for the count query
            data_query_params: Parameters for the data query
            offset: Pagination offset
            limit: Number of items per page
            result_key: Key name for the results in the response
            
        Returns:
            Dictionary with total count, next_offset, and results
        """
        # Get count
        if callable(count_query):
            count_query_str = count_query()
        else:
            count_query_str = count_query
            
        count_df = db.frameResponse(count_query_str, count_query_params)
        
        total_count = 0
        if not count_df.empty:
            total_count = int(count_df.iloc[0]['count'])

        # If no results found, return empty result
        if total_count == 0:
            return {
                "total": 0,
                "next_offset": None,
                result_key: []
            }

        # Get data
        if callable(data_query):
            data_query_str = data_query(offset, limit)
        else:
            data_query_str = data_query
            
        data_df = db.frameResponse(data_query_str, data_query_params)
        
        results = []
        if not data_df.empty:
            results = [convert_numpy_types(r) for r in data_df.to_dict(orient="records")]

        return {
            "total": total_count,
            "next_offset": offset + limit if offset + limit < total_count else None,
            result_key: results
        }

    @staticmethod
    def get_count_query(table: str, owner_join_column: bool = False) -> str:
        """Generate count query for a table."""
        if owner_join_column:
            return f"""
                SELECT COUNT(*) AS count
                FROM {table} t
                JOIN vaults v ON t.vault_id = v.vault_id
                JOIN users u ON t.user_id = u.user_id
                WHERE u.address = %s
                AND v.chain_id = %s
            """
        else:
            return f"""
                SELECT COUNT(*) AS count
                FROM {table} t
                JOIN vaults v ON t.vault_id = v.vault_id
                WHERE (t.from_address = %s OR t.to_address = %s)
                AND t.from_address != ALL(%s)
                AND t.to_address != ALL(%s)
                AND v.chain_id = %s
            """

    @staticmethod
    def get_vault_snapshots_count_query() -> str:
        """Count query for vault snapshots."""
        return """
            SELECT COUNT(*) AS count
            FROM vault_snapshots t
            JOIN vaults v ON t.vault_id = v.vault_id
            WHERE t.vault_id = %s
            AND v.chain_id = %s
        """

    @staticmethod
    def get_user_position_count_query() -> str:
        """Count query for user positions."""
        return """
            SELECT COUNT(DISTINCT v.vault_id) AS count
            FROM vaults v
            JOIN users u ON u.address = %s AND u.chain_id = %s
            WHERE v.chain_id = %s
        """ 
    
    @staticmethod
    def get_integrated_position_count_query() -> str:
        return """
            SELECT COUNT(DISTINCT vr.vault_id) AS count
            FROM vault_returns vr
            WHERE vr.user_id = %s
            AND vr.vault_id = %s
        """
