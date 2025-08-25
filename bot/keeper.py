import os
import time
import asyncio
from dotenv import load_dotenv
from safe_tx_utils import keeper_txs_handler
import requests

load_dotenv()

def fetch_keeper_txs(api_url, chain_id):
    url = f"{api_url}/lagoon/keeper_txs/test/{chain_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def run_bot(chain_id, api_url):
    try:
        pending = fetch_keeper_txs(api_url, chain_id)
        vaults_txs = pending.get("vaults_txs", [])
        if len(vaults_txs) == 0:
            print(f"No vaults found for chain {chain_id}")
            return

        keeper_txs_handler(chain_id, vaults_txs)
    except Exception as e:
        print(f"Bot execution failed: {e}")
        raise

async def run_bot_loop(chain_id, api_url, sleep_interval):
    while True:
        try:
            print(f"\n--- Bot cycle started for chain {chain_id} at {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
            run_bot(chain_id, api_url)
            print(f"--- Bot cycle completed for chain {chain_id}, sleeping for {sleep_interval} seconds ---")
            await asyncio.sleep(sleep_interval)
        except KeyboardInterrupt:
            print(f"\nBot stopped by user on chain {chain_id}")
            break
        except Exception as e:
            print(f"Bot loop error on chain {chain_id}: {e}")
            print(f"Retrying in {sleep_interval} seconds...")
            await asyncio.sleep(sleep_interval)

async def run_parallel_bots(api_url):
    print("Starting keeper bot in infinite loop mode.....")
    sleep_interval = int(os.getenv("BOT_SLEEP_INTERVAL", "60"))

    chain_ids = os.getenv("SUPPORTED_CHAINS", "")
    if not chain_ids:
        raise ValueError("SUPPORTED_CHAINS env var must be defined")

    chain_ids = [int(cid.strip()) for cid in chain_ids.split(",")]

    tasks = [
        asyncio.create_task(
            run_bot_loop(
                chain_id=chain_id,
                api_url=api_url,
                sleep_interval=sleep_interval,
            )
        )
        for chain_id in chain_ids
    ]

    await asyncio.gather(*tasks)
    
def wait_for_api_ready(url: str, timeout: int = 60, retry_interval: int = 3):
    print(f"Waiting for API to be ready at {url}...")
    start = time.time()
    while True:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print("API is ready.")
                return
        except Exception as e:
            print(f"Still waiting: {e}")

        if time.time() - start > timeout:
            raise TimeoutError(f"API did not become ready within {timeout} seconds.")
        time.sleep(retry_interval)

if __name__ == "__main__":
    api_url = os.getenv("API_URL", "http://damm-api:8000")
    wait_for_api_ready(api_url, timeout=20, retry_interval=3)
    asyncio.run(run_parallel_bots(api_url))
