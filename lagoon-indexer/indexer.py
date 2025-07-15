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
from core.lagoon_deployments import get_lagoon_deployments
from db.register_indexer import register_indexer

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
    "Referral",
    "StateUpdated",
    "Paused",
    "Unpaused"
]

async def run_indexer(
    chain_id: int,
    lagoon_address: str,
    sleep_time: int,
    range: int,
    real_time: bool,
    run_time: int
) -> None:
    vault_id = register_indexer(chain_id, lagoon_address)

    indexer = LagoonIndexer(
        lagoon_abi=LAGOON_ABI,
        chain_id=chain_id,
        sleep_time=sleep_time,
        range=range,
        event_names=events_to_track,
        real_time=real_time,
        vault_id=vault_id,
    )

    start_time = time.time()
    print(f"[{chain_id}] Indexer started.")

    while time.time() - start_time < run_time:
        try:
            if await indexer.fetcher_loop() == 1:
                break
        except Exception as e:
            print(f"[{chain_id}] Error in fetcher loop: {e}")
            traceback.print_exc()
            print(f"[{chain_id}] Sleeping {sleep_time}s before retrying...")
            await asyncio.sleep(sleep_time)

    print(f"[{chain_id}] Indexer exited after {time.time() - start_time:.2f}s.")

async def launch_forever(
    chain_id: int,
    lagoon_address: str,
    sleep_time: int,
    range: int,
    real_time: bool,
    run_time: int
) -> None:
    while True:
        try:
            await run_indexer(chain_id, lagoon_address, sleep_time, range, real_time, run_time)
        except Exception as e:
            print(f"[{chain_id}] Indexer crashed: {e}")
            traceback.print_exc()
        print(f"[{chain_id}] Restarting in 5 seconds...\n")
        await asyncio.sleep(5)

async def main() -> None:
    load_dotenv()

    chain_ids = os.getenv("SUPPORTED_CHAINS", "")
    if not chain_ids:
        raise ValueError("SUPPORTED_CHAINS env var must be defined")

    chain_ids = [int(cid.strip()) for cid in chain_ids.split(",")]

    parser = argparse.ArgumentParser(description='Lagoon Multi-Chain Indexer')
    parser.add_argument('--sleep_time', type=int, required=True, help='Sleep time between fetches')
    parser.add_argument('--range', type=int, required=True, help='Block range to process per iteration')
    parser.add_argument('--real_time', type=int, choices=[0, 1], required=True, help='1 = real-time, 0 = one-shot')
    parser.add_argument('--run_time', type=int, required=True, help='Indexer run time in seconds before recycle')

    args = parser.parse_args()

    tasks = [
        asyncio.create_task(
            launch_forever(
                chain_id=chain_id,
                lagoon_address=get_lagoon_deployments(chain_id)["lagoon_address"],
                sleep_time=args.sleep_time,
                range=args.range,
                real_time=bool(args.real_time),
                run_time=args.run_time,
            )
        )
        for chain_id in chain_ids
    ]

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Fatal error in top-level indexer: {e}")
        traceback.print_exc()
