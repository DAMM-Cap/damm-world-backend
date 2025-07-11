from dotenv import load_dotenv
import os
import sys
import argparse
import time
import traceback
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lagoon_indexer import LagoonIndexer
from constants.abi.lagoon import LAGOON_ABI
from db.register_indexer import register_indexer

async def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description='Lagoon Indexer')
    parser.add_argument('chain_id', type=int, help='Chain ID')
    parser.add_argument('sleep_time', type=int, help='Sleep time between iterations')
    parser.add_argument('range', type=int, help='Block range to process')
    parser.add_argument('real_time', type=int, help='Whether to run in real-time mode (1) or one-shot (0)')
    parser.add_argument('run_time', type=int, help='Run time in seconds')

    args = parser.parse_args()

    vault_id = register_indexer(args.chain_id)

    real_time = bool(args.real_time)

    events_to_track = [
        "DepositRequest", 
        "RedeemRequest", 
        "SettleDeposit", 
        "SettleRedeem", 
        "Deposit", 
        "Withdraw", 
        "DepositRequestCanceled", 
        "Transfer", 
        "NewTotalAssetsUpdated",
        "RatesUpdated",
        "Referral"
    ]

    indexer = LagoonIndexer(
        lagoon_abi=LAGOON_ABI,
        chain_id=args.chain_id,
        sleep_time=args.sleep_time,
        range=args.range,
        event_names=events_to_track,
        real_time=real_time,
        vault_id=vault_id, 
    )

    start_time = time.time()
    print("Lagoon Indexer is starting...")

    while time.time() - start_time < args.run_time:
        try:
            if await indexer.fetcher_loop() == 1:
                break
        except Exception as e:
            print(f"Error in indexer loop: {e}")
            traceback.print_exc()
            print(f"Sleeping {args.sleep_time} seconds before retrying...")
            time.sleep(args.sleep_time)

    print(f"Indexer stopped after {time.time() - start_time:.2f} seconds.")

if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
        except Exception as e:
            print(f"Uncaught error in main loop: {e}")
            traceback.print_exc()

        print("Main indexer loop completed. Restarting in 5 seconds...\n")
        time.sleep(5)
