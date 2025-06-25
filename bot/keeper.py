import os
import time
from dotenv import load_dotenv
#from tx_utils import keeper_txs_handler
from safe_tx_utils import keeper_txs_handler
import requests

load_dotenv()

def fetch_keeper_txs(chain_id):
    url = f"http://damm-api:8000/lagoon/keeper_txs/test/{chain_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def run_bot():
    try:
        chain_id = int(os.getenv("CHAIN_ID", "480"))
        pending = fetch_keeper_txs(chain_id)

        if len(pending['vaults_txs']) == 0:
            print("No pending transactions found")
            return

        print(f"Found {len(pending['vaults_txs'])} pending transactions to trigger")
        
        keeper_txs_handler(chain_id, pending) ## Uncomment this to trigger keeper txs
    except Exception as e:
        print(f"Bot execution failed: {e}")
        raise

def run_bot_loop():
    print("Starting keeper bot in infinite loop mode.....")
    sleep_interval = int(os.getenv("BOT_SLEEP_INTERVAL", "60"))

    while True:
        try:
            print(f"\n--- Bot cycle started at {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
            run_bot()
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
    wait_for_api_ready("http://damm-api:8000", timeout=20, retry_interval=3)
    run_bot_loop()
