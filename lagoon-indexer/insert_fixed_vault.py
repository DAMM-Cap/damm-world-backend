import os
import psycopg2
from dotenv import load_dotenv
from core.lagoon_deployments import get_lagoon_deployments

load_dotenv()

DB_PARAMS = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT', '5432')
}

def insert_fixed_vaults():
    lagoon_address_anvil = get_lagoon_deployments(31337)["lagoon_address"]
    wld_token_address_anvil = get_lagoon_deployments(31337)["wld_token"]
    lagoon_address_worldchain = get_lagoon_deployments(480)["lagoon_address"]
    wld_token_address_worldchain = get_lagoon_deployments(480)["wld_token"]
    query = """
    INSERT INTO vaults (
        vault_id, chain_id, name, vault_token_symbol, vault_token_address,
        deposit_token_symbol, deposit_token_address
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s
    )
    ON CONFLICT (vault_id) DO NOTHING;
    """

    with psycopg2.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            # ANVIL
            cur.execute(query, (
                1,
                31337,
                'WLD/USDC',
                'vWLD',
                lagoon_address_anvil,
                'WLD',
                wld_token_address_anvil
            ))
            # WORLDCHAIN
            cur.execute(query, (
                2,
                480,
                'WLD/USDC',
                'vWLD',
                lagoon_address_worldchain,
                'WLD',
                wld_token_address_worldchain
            ))
        conn.commit()
    print("Fixed vault row inserted (or already exists).")

if __name__ == "__main__":
    insert_fixed_vaults()
