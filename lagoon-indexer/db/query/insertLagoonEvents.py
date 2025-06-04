from pandas import DataFrame
from db.db import Database

def insert_lagoon_events(event_df: DataFrame, table_name: str, db: Database):
    filtered_cols = [c for c in event_df.columns]
    cleaned_df = event_df[filtered_cols]
    
    db.insertDf(cleaned_df, table_name)
