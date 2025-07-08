from db.db import Database

class LagoonEventsHelpers:
    @staticmethod
    def fetch_wallets_and_tx_hashes(db: Database, user_ids: list[str], event_ids: list[str]) -> tuple[list[str], list[str]]:
        """
        Given lists of user_ids and event_ids, fetch corresponding wallets and transaction hashes.
        """
        conn = db.connection
        wallets = []
        txs_hashes = []

        with conn.cursor() as cur:
            if user_ids:
                cur.execute("""
                    SELECT address
                    FROM users
                    WHERE user_id = ANY(%s::uuid[]);
                """, (user_ids,))
                wallets = [row[0] for row in cur.fetchall()]

            if event_ids:
                cur.execute("""
                    SELECT DISTINCT transaction_hash
                    FROM events
                    WHERE event_id = ANY(%s::uuid[]);
                """, (event_ids,))
                txs_hashes = [row[0] for row in cur.fetchall()]

        return wallets, txs_hashes
