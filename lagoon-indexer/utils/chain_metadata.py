import requests

def get_chain_metadata(chain_id: int):
    url = "https://chainid.network/chains.json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        chains = response.json()
        chain = next((c for c in chains if c["chainId"] == chain_id), None)
        if not chain:
            print(f"No chain found with ID {chain_id}")
            return None
        return {
            "chain_id": chain["chainId"],
            "name": chain.get("name"),
            "network": chain.get("network"),
            "network_type": "mainnet" if not chain.get("testnet", False) else "testnet",
            "native_currency_symbol": chain.get("nativeCurrency", {}).get("symbol"),
            "explorer_url": chain.get("explorers", [{}])[0].get("url"),
        }
    except Exception as e:
        print("Error fetching chain metadata:", e)
        return None
