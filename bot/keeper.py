import os
import time
from dotenv import load_dotenv
from safe_tx_utils import keeper_txs_handler
import requests

load_dotenv()

def fetch_keeper_txs(api_url, chain_id):
    url = f"{api_url}/lagoon/keeper_txs/test/{chain_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def run_bot(api_url):
    try:
        chain_id = int(os.getenv("CHAIN_ID", "480"))
        pending = fetch_keeper_txs(api_url, chain_id)
        
        # Handle different response statuses
        if pending.get("status") == "syncing":
            print(pending.get("message", "Indexer is syncing"))
            return
        if pending.get("status") == "error":
            raise Exception(pending.get("message", "Unknown error"))
        if pending.get("status") == "ok":
            # Check if there are any transactions
            vaults_txs = pending.get("vaults_txs", [])
            if len(vaults_txs) == 0:
                print("No pending transactions found")
                return

            print(f"Found {len(vaults_txs)} pending transactions to trigger")
            
            # Create the expected structure for keeper_txs_handler
            pending_data = {"vaults_txs": vaults_txs}
            keeper_txs_handler(chain_id, pending_data)
        else:
            # Fallback for unexpected response format
            print(f"Unexpected response format: {pending}")
            return
            
    except Exception as e:
        print(f"Bot execution failed: {e}")
        raise

def run_bot_loop(api_url):
    print("Starting keeper bot in infinite loop mode.....")
    sleep_interval = int(os.getenv("BOT_SLEEP_INTERVAL", "60"))

    while True:
        try:
            print(f"\n--- Bot cycle started at {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
            run_bot(api_url)
            print(f"--- Bot cycle completed, sleeping for {sleep_interval} seconds ---")
            time.sleep(sleep_interval)
        except KeyboardInterrupt:
            print("\nBot stopped by user")
            break
        except Exception as e:
            print(f"Bot loop error: {e}")
            print(f"Retrying in {sleep_interval} seconds...")
            time.sleep(sleep_interval)

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
    run_bot_loop(api_url)
