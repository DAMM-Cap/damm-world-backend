from dotenv import load_dotenv
import os
import sys
import time
import traceback
import pandas as pd
from typing import List, Dict
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.db import Database, getEnvDb
from db.query.insertLagoonEvents import insert_lagoon_events
from core.blockchain import getEnvNode
from core.lagoon_deployments import get_lagoon_deployments
from db.lagoon_db_utils import LagoonDbUtils

# Event Formatter
class EventFormatter:
    @staticmethod
    def _common_fields(event: Dict, vault_id: int) -> Dict:
        return {
            'vault_id': vault_id,
            'block': int(event['blockNumber']),
            'log_index': int(event['logIndex']),
            'tx_hash': event['transactionHash'].hex(),
        }

    @staticmethod
    def format_DepositRequest_data(event: Dict, vault_id: int) -> Dict:
        data = EventFormatter._common_fields(event, vault_id)
        data.update({
            'request_id': int(event['args']['requestId']),
            'controller': event['args']['controller'].lower(),
            'owner': event['args']['owner'].lower(),
            'sender': event['args']['sender'].lower(),
            'assets': int(event['args']['assets']),
            'status': 'pending',
            'timestamp': event['blockTimestamp'],
            'status_updated_at': event['blockTimestamp']
        })
        return data
    
    @staticmethod
    def format_RedeemRequest_data(event: Dict, vault_id: int) -> Dict:
        data = EventFormatter._common_fields(event, vault_id)
        data.update({
            'request_id': int(event['args']['requestId']),
            'controller': event['args']['controller'].lower(),
            'owner': event['args']['owner'].lower(),
            'sender': event['args']['sender'].lower(),
            'shares': int(event['args']['shares']),
            'status': 'pending',
            'timestamp': event['blockTimestamp'],
            'status_updated_at': event['blockTimestamp']
        })
        return data
    
    @staticmethod
    def format_SettleDeposit_data(event: Dict, vault_id: int) -> Dict:
        data = EventFormatter._common_fields(event, vault_id)
        data.update({
            'epoch_id': int(event['args']['epochId']),
            'settled_id': int(event['args']['settledId']),
            'total_assets': int(event['args']['totalAssets']),
            'total_supply': int(event['args']['totalSupply']),
            'assets_deposited': int(event['args']['assetsDeposited']),
            'shares_minted': int(event['args']['sharesMinted']),
            'timestamp': event['blockTimestamp'],
        })
        return data

    @staticmethod
    def format_SettleRedeem_data(event: Dict, vault_id: int) -> Dict:
        data = EventFormatter._common_fields(event, vault_id)
        data.update({
            'epoch_id': int(event['args']['epochId']),
            'settled_id': int(event['args']['settledId']),
            'total_assets': int(event['args']['totalAssets']),
            'total_supply': int(event['args']['totalSupply']),
            'assets_withdrawed': int(event['args']['assetsWithdrawed']),
            'shares_burned': int(event['args']['sharesBurned']),
            'timestamp': event['blockTimestamp'],
        })
        return data

    @staticmethod
    def format_DepositRequestCanceled_data(event: Dict, vault_id: int) -> Dict:
        data = EventFormatter._common_fields(event, vault_id)
        data.update({
            'request_id': int(event['args']['requestId']),
            'controller': event['args']['controller'],
            'timestamp': event['blockTimestamp'],
        })
        return data

    @staticmethod
    def format_Transfer_data(event: Dict, vault_id: int) -> Dict:
        data = EventFormatter._common_fields(event, vault_id)
        data.update({
            'from_address': event['args']['from'].lower(),
            'to_address': event['args']['to'].lower(),
            'value': int(event['args']['value']),
            'timestamp': event['blockTimestamp'],
        })
        return data
    
    @staticmethod
    def format_NewTotalAssetsUpdated_data(event: Dict, vault_id: int) -> Dict:
        data = EventFormatter._common_fields(event, vault_id)
        data.update({
            'total_assets': int(event['args']['totalAssets']),
            'timestamp': event['blockTimestamp'],
        })
        return data

    @staticmethod
    def format_Withdraw_data(event: Dict, vault_id: int) -> Dict:
        data = EventFormatter._common_fields(event, vault_id)
        data.update({
            'sender': event['args']['sender'].lower(),
            'receiver': event['args']['receiver'].lower(),
            'owner': event['args']['owner'].lower(),
            'assets': int(event['args']['assets']),
            'shares': int(event['args']['shares']),
            'timestamp': event['blockTimestamp'],
        })
        return data

# Event Processor
class EventProcessor:
    def __init__(self, db: Database, vault_id: int):
        self.db = db
        self.vault_id = vault_id
        self.EVENT_TABLES = {
            'DepositRequest': 'lagoon_depositrequest',
            'RedeemRequest': 'lagoon_redeemrequest',
            'SettleDeposit': 'lagoon_settledeposit',
            'SettleRedeem': 'lagoon_settleredeem',
            'DepositRequestCanceled': 'lagoon_depositrequestcanceled',
            'Transfer': 'lagoon_transfer',
            'NewTotalAssetsUpdated': 'lagoon_newtotalassetsupdated',
            'Withdraw': 'lagoon_withdraw'
        }

    def save_to_db_batch(self, event_name: str, event_data_list: List[Dict]):
        if not event_data_list:
            return
        df = pd.DataFrame(event_data_list)
        table_name = self.EVENT_TABLES.get(event_name)

        # Convert timestamp columns to datetime objects
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s').dt.strftime('%Y-%m-%d %H:%M:%S')
        if 'status_updated_at' in df.columns:
            df['status_updated_at'] = pd.to_datetime(df['status_updated_at'], unit='s').dt.strftime('%Y-%m-%d %H:%M:%S')

        if table_name:
            insert_lagoon_events(df, table_name, self.db)
            print(f"Saved {len(event_data_list)} {event_name} events to {table_name}.")

    def store_DepositRequest_events(self, events: List[Dict]):
        event_data_list = [
            EventFormatter.format_DepositRequest_data(event, self.vault_id)
            for event in events
        ]
        self.save_to_db_batch('DepositRequest', event_data_list)

    def store_RedeemRequest_events(self, events: List[Dict]):
        event_data_list = [
            EventFormatter.format_RedeemRequest_data(event, self.vault_id)
            for event in events
        ]
        self.save_to_db_batch('RedeemRequest', event_data_list)

    def store_SettleDeposit_events(self, events: List[Dict]):
        event_data_list = [
            EventFormatter.format_SettleDeposit_data(event, self.vault_id)
            for event in events
        ]
        self.save_to_db_batch('SettleDeposit', event_data_list)

    def store_SettleRedeem_events(self, events: List[Dict]):
        event_data_list = [
            EventFormatter.format_SettleRedeem_data(event, self.vault_id)
            for event in events
        ]
        self.save_to_db_batch('SettleRedeem', event_data_list)

    def store_DepositRequestCanceled_events(self, events: List[Dict]):
        event_data_list = [
            EventFormatter.format_DepositRequestCanceled_data(event, self.vault_id)
            for event in events
        ]
        self.save_to_db_batch('DepositRequestCanceled', event_data_list)

    def store_Transfer_events(self, events: List[Dict]):
        event_data_list = [
            EventFormatter.format_Transfer_data(event, self.vault_id)
            for event in events
        ]
        self.save_to_db_batch('Transfer', event_data_list)

    def store_NewTotalAssetsUpdated_events(self, events: List[Dict]):
        event_data_list = [
            EventFormatter.format_NewTotalAssetsUpdated_data(event, self.vault_id)
            for event in events
        ]
        self.save_to_db_batch('NewTotalAssetsUpdated', event_data_list)

    def store_Withdraw_events(self, events: List[Dict]):
        event_data_list = [
            EventFormatter.format_Withdraw_data(event, self.vault_id)
            for event in events
        ]
        self.save_to_db_batch('Withdraw', event_data_list)


# Lagoon Indexer
class LagoonIndexer:
    def __init__(self, lagoon_abi: list, chain_id: int, sleep_time: int, range: int, event_names: list, real_time: bool = True, vault_id: int = None):
        lagoon_deployments = get_lagoon_deployments(chain_id)
        self.first_lagoon_block = lagoon_deployments['genesis_block_lagoon']
        self.lagoon = lagoon_deployments['lagoon_address']
        self.vault_id = vault_id
        self.chain_id = chain_id
        self.sleep_time = sleep_time
        self.range = range
        self.real_time = real_time
        self.event_names = event_names

        self.blockchain = getEnvNode(chain_id)
        self.lagoon_contract = self.blockchain.node.eth.contract(
            address=self.lagoon,
            abi=lagoon_abi
        )
        self.db = getEnvDb('damm-public')
        self.event_processor = EventProcessor(self.db, self.vault_id)

    def get_block_ts(self, event: Dict) -> datetime:
        block_number = int(event['blockNumber'])
        block = self.blockchain.node.eth.get_block(block_number)
        return datetime.fromtimestamp(block['timestamp'])

    def get_latest_block_number(self) -> int:
        return self.blockchain.getLatestBlockNumber()

    def fetch_events(self, event_name: str, from_block: int, to_block: int) -> List[Dict]:
        """
        Fetches events of specified type within the given block range.
        """
        event_filter = self.lagoon_contract.events[event_name].create_filter(
            fromBlock=from_block,
            toBlock=to_block
        )
        return event_filter.get_all_entries()

    def fetch_and_store(self, from_block: int, range: int):
        """
        Fetches and stores events for all configured event types.
        """
        to_block = from_block + range
        for event_name in self.event_names:
            try:
                print(f"Fetching {event_name} events from block {from_block} to {to_block}")
                events = self.fetch_events(event_name, from_block, to_block)
                if not events:
                    print(f"No {event_name} events found in block range {from_block}-{to_block}")
                    continue

                # Create fresh dict copies with blockTimestamp added
                new_events = []
                for event in events:
                    event_copy = dict(event)
                    event_copy['blockTimestamp'] = self.get_block_ts(event)
                    new_events.append(event_copy)
                events = new_events  # Replace the list with the new one

                if event_name == 'DepositRequest':
                    self.event_processor.store_DepositRequest_events(events)
                elif event_name == 'RedeemRequest':
                    self.event_processor.store_RedeemRequest_events(events)
                if event_name == 'SettleDeposit':
                    self.event_processor.store_SettleDeposit_events(events)
                elif event_name == 'SettleRedeem':
                    self.event_processor.store_SettleRedeem_events(events)
                elif event_name == 'DepositRequestCanceled':
                    self.event_processor.store_DepositRequestCanceled_events(events)
                elif event_name == 'Transfer':
                    self.event_processor.store_Transfer_events(events)
                elif event_name == 'NewTotalAssetsUpdated':
                    self.event_processor.store_NewTotalAssetsUpdated_events(events)
                elif event_name == 'Withdraw':
                    self.event_processor.store_Withdraw_events(events)
            except Exception as e:
                print(f"Error fetching/storing {event_name} events: {e}")
                traceback.print_exc()
                time.sleep(5)
                self.blockchain = getEnvNode(self.chain_id)

    def fetcher_loop(self):
        """
        Processes a single range of blocks and updates the last processed block in the DB.
        Returns 1 if up to date.
        """
        try:
            last_processed_block = LagoonDbUtils.get_last_processed_block(self.db, self.vault_id, self.first_lagoon_block)
            print(f"Last processed block: {last_processed_block}")

            latest_block = self.get_latest_block_number()
            print(f"Current chain head: {latest_block}")

            block_gap = latest_block - last_processed_block
            if block_gap < 1:
                print("Lagoon is up to date.")
                return 1

            range_to_process = min(self.range, block_gap)
            from_block = last_processed_block + 1
            print(f"Processing block range {from_block} to {from_block + range_to_process}")

            self.fetch_and_store(from_block, range_to_process)
            LagoonDbUtils.update_last_processed_block(self.db, self.vault_id, from_block + range_to_process)
            print(f"Updated last processed block to {from_block + range_to_process} in DB.")

            if self.real_time and self.sleep_time > 0:
                print(f"Sleeping {self.sleep_time} seconds.")
                time.sleep(self.sleep_time)

        except Exception as e:
            print(f"Error in fetcher loop: {e}")
            traceback.print_exc()
            print(f"Sleeping {self.sleep_time} seconds before retrying.")
            time.sleep(self.sleep_time)
            return 1
