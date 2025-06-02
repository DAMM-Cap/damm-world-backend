from web3 import Web3
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

import os
import argparse
from lagoon_indexer import LagoonIndexer
import time
from constants.abi.lagoon import LAGOON_ABI

""" 
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

def main():
    print("Indexer is starting...")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT now()"))
        print(f"Database time: {result.fetchone()[0]}")

 """

def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description='Lagoon Indexer')
    parser.add_argument('chain_id', type=int, help='Chain ID')
    parser.add_argument('sleep_time', type=int, help='Sleep time between iterations')
    parser.add_argument('range', type=int, help='Block range to process')
    parser.add_argument('real_time', type=int, help='Whether to run in real-time mode')
    parser.add_argument('run_time', type=int, help='Run time in seconds')


    args = parser.parse_args()
    real_time = bool(args.real_time)

    events_to_track = ["SettleDeposit", "SettleRedeem", "DepositRequestCanceled"]

    indexer = LagoonIndexer(
        lagoon_abi=LAGOON_ABI,
        chain_id=args.chain_id,
        sleep_time=args.sleep_time,
        range=args.range,
        event_names=events_to_track,
        real_time=real_time,
    )
    #there are two ways to break the loop in different places because we need to verify the runtime BEFORE
    start_time = time.time()
    
    while time.time() - start_time < args.run_time:
        if indexer.fetcher_loop() == 1:
            break

    print(f"Indexer stopped after {time.time() - start_time} seconds")


if __name__ == "__main__":
    main()
