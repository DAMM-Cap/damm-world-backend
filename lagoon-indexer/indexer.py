from web3 import Web3
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

def main():
    print("Indexer is starting...")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT now()"))
        print(f"Database time: {result.fetchone()[0]}")

if __name__ == "__main__":
    main()
