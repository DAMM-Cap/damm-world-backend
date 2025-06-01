from pandas import DataFrame
from db.db import Database

def insert_lagoon_events(event_df: DataFrame, table_name: str, db: Database):
    # Remove columns that should not be stored
    exclude_columns = ['contract_address', 'chain_id']  # if applicable
    filtered_cols = [c for c in event_df.columns if c not in exclude_columns]
    cleaned_df = event_df[filtered_cols]

    db.insertDf(cleaned_df, table_name)
