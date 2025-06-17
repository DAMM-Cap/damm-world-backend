from dotenv import load_dotenv
import os
import sys
import time
import traceback
import pandas as pd
from typing import List, Dict, Tuple
from datetime import datetime
import uuid
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.db import Database, getEnvDb
from core.blockchain import getEnvNode
from core.lagoon_deployments import get_lagoon_deployments
from db.query.lagoon_db_utils import LagoonDbUtils
from db.query.lagoon_events import LagoonEvents
from db.utils.lagoon_db_date_utils import LagoonDbDateUtils
from eth_utils import event_abi_to_log_topic

# Event Formatter
class EventFormatter:
    @staticmethod
    def _common_fields(event: Dict, vault_id: str, event_type: str) -> Dict:
        return {
            'event_id': str(uuid.uuid4()),
            'vault_id': vault_id,
            'event_type': event_type,
            'block_number': int(event['blockNumber']),
            'log_index': int(event['logIndex']),
            'transaction_hash': event['transactionHash'].hex(),
            'transaction_status': 'confirmed',
            'event_timestamp': event['blockTimestamp']
        }

    @staticmethod
    def format_DepositRequest_data(db: Database, event: Dict, vault_id: str, chain_id: int) -> Tuple[Dict, Dict]:
        event_data = EventFormatter._common_fields(event, vault_id, 'deposit_request')
        deposit_data = {
            'request_id': int(event['args']['requestId']),
            'event_id': event_data['event_id'],
            'vault_id': event_data['vault_id'],
            'user_id': LagoonDbUtils.get_user_id(db, event['args']['owner'].lower(), chain_id),
            'sender_address': event['args']['sender'].lower(),
            'controller_address': event['args']['controller'].lower(),
            'referral_address': event['args'].get('referral', '').lower() if event['args'].get('referral') else None,
            'assets': int(event['args']['assets']),
            'status': 'pending',
            'updated_at': event_data['event_timestamp'],
            'settled_at': None
        }
        return event_data, deposit_data

    @staticmethod
    def format_RedeemRequest_data(db: Database, event: Dict, vault_id: str, chain_id: int) -> Tuple[Dict, Dict]:
        event_data = EventFormatter._common_fields(event, vault_id, 'redeem_request')
        redeem_data = {
            'request_id': int(event['args']['requestId']),
            'event_id': event_data['event_id'],
            'vault_id': event_data['vault_id'],
            'user_id': LagoonDbUtils.get_user_id(db, event['args']['owner'].lower(), chain_id),
            'sender_address': event['args']['sender'].lower(),
            'controller_address': event['args']['controller'].lower(),
            'shares': int(event['args']['shares']),
            'status': 'pending',
            'updated_at': event_data['event_timestamp'],
            'settled_at': None
        }
        return event_data, redeem_data
    
    @staticmethod
    def format_Settlement_data(event: Dict, vault_id: str, settlement_type: str) -> Tuple[Dict, Dict]:
        event_type = 'settle_' + settlement_type
        event_data = EventFormatter._common_fields(event, vault_id, event_type)
        settle_data = {
            'event_id': event_data['event_id'],
            'vault_id': event_data['vault_id'],
            'settlement_type': settlement_type,
            'epoch_id': int(event['args']['epochId']),
        }
        return event_data, settle_data

    @staticmethod
    def format_DepositRequestCanceled_data(event: Dict, vault_id: str) -> Tuple[Dict, Dict]:
        event_data = EventFormatter._common_fields(event, vault_id, 'deposit_request_canceled')
        deposit_request_canceled_data = {
            'request_id': int(event['args']['requestId']),
        }
        return event_data, deposit_request_canceled_data

    @staticmethod
    def format_Transfer_data(event: Dict, vault_id: str) -> Tuple[Dict, Dict]:
        event_data = EventFormatter._common_fields(event, vault_id, 'transfer')
        transfer_data = {
            'event_id': event_data['event_id'],
            'vault_id': event_data['vault_id'],
            'from_address': event['args']['from'].lower(),
            'to_address': event['args']['to'].lower(),
            'amount': int(event['args']['value']),
        }
        return event_data, transfer_data
    
    @staticmethod
    def format_NewTotalAssetsUpdated_data(event: Dict, vault_id: str) -> Tuple[Dict, Dict]:
        event_data = EventFormatter._common_fields(event, vault_id, 'total_assets_updated')
        new_total_assets_updated_data = {
            'event_id': event_data['event_id'],
            'vault_id': event_data['vault_id'],
            'total_assets': int(event['args']['totalAssets']),
            'total_shares': None, #int(event['args']['totalShares']),
            'share_price': None, #int(event['args']['sharePrice']),
            'management_fee': None, #int(event['args']['managementFee']),
            'performance_fee': None, #int(event['args']['performanceFee']),
            'apy': None #int(event['args']['apy'])
        }
        return event_data, new_total_assets_updated_data

    @staticmethod
    def format_Return_data(db: Database, event: Dict, vault_id: str, chain_id: int, return_type: str) -> Tuple[Dict, Dict]:
        event_data = EventFormatter._common_fields(event, vault_id, return_type)
        return_data = {
            'event_id': event_data['event_id'],
            'vault_id': event_data['vault_id'],
            'user_id': LagoonDbUtils.get_user_id(db, event['args']['owner'].lower(), chain_id),
            'return_type': return_type,
            'assets': int(event['args']['assets']),
            'shares': int(event['args']['shares']),
        }
        return event_data, return_data
    
# Event Processor
class EventProcessor:
    def __init__(self, db: Database, vault_id: str, chain_id: int):
        self.db = db
        self.vault_id = vault_id
        self.chain_id = chain_id
        self.EVENT_TABLES = {
            'DepositRequest': 'deposit_requests',
            'RedeemRequest': 'redeem_requests',
            'SettleDeposit': 'settlements',
            'SettleRedeem': 'settlements',
            'DepositRequestCanceled': 'deposit_request_canceled',
            'Transfer': 'transfers',
            'NewTotalAssetsUpdated': 'vault_snapshots',
            'Deposit': 'vault_returns',
            'Withdraw': 'vault_returns'
        }

    def save_to_db_batch(self, event_name: str, event_data_list: List[Dict]):
        if not event_data_list:
            return
        df = pd.DataFrame(event_data_list)
        table_name = 'events' if event_name == 'events' else self.EVENT_TABLES.get(event_name)

        if table_name:
            LagoonEvents.insert_lagoon_events(self.db, df, table_name)
            print(f"Saved {len(event_data_list)} {event_name} events to {table_name}.")

    def store_DepositRequest_events(self, events: List[Dict]):
        event_rows = []
        deposit_rows = []
        for event in events:
            event_data, deposit_data = EventFormatter.format_DepositRequest_data(self.db, event, self.vault_id, self.chain_id)
            event_rows.append(event_data)
            deposit_rows.append(deposit_data)

        self.save_to_db_batch('events', event_rows)
        self.save_to_db_batch('DepositRequest', deposit_rows)

    def store_RedeemRequest_events(self, events: List[Dict]):
        event_rows = []
        redeem_rows = []
        for event in events:
            event_data, redeem_data = EventFormatter.format_RedeemRequest_data(self.db, event, self.vault_id, self.chain_id)
            event_rows.append(event_data)
            redeem_rows.append(redeem_data)

        self.save_to_db_batch('events', event_rows)
        self.save_to_db_batch('RedeemRequest', redeem_rows)

    def store_SettleDeposit_events(self, events: List[Dict]):
        event_data_list = []
        settle_data_list = []
        for event in events:
            event_data, settle_data = EventFormatter.format_Settlement_data(event, self.vault_id, 'deposit')
            event_data_list.append(event_data)
            settle_data_list.append(settle_data)

            # UPDATE the matching DepositRequest status
            LagoonEvents.update_settled_deposit_requests(
                self.db,
                self.vault_id,
                event_data['event_timestamp']
            )

        self.save_to_db_batch('events', event_data_list)
        self.save_to_db_batch('SettleDeposit', settle_data_list)

    def store_SettleRedeem_events(self, events: List[Dict]):
        event_data_list = []
        settle_data_list = []
        for event in events:
            event_data, settle_data = EventFormatter.format_Settlement_data(event, self.vault_id, 'redeem')
            event_data_list.append(event_data)
            settle_data_list.append(settle_data)

            # UPDATE the matching RedeemRequest status
            LagoonEvents.update_settled_redeem_requests(
                self.db,
                self.vault_id,
                event_data['event_timestamp']
            )

        self.save_to_db_batch('events', event_data_list)
        self.save_to_db_batch('SettleRedeem', settle_data_list)
    
    def store_DepositRequestCanceled_events(self, events: List[Dict]):
        event_data_list = []
        for event in events:
            event_data, deposit_request_canceled_data = EventFormatter.format_DepositRequestCanceled_data(event, self.vault_id)
            event_data_list.append(event_data)

            # UPDATE the matching DepositRequest status
            LagoonEvents.update_canceled_deposit_request(
                self.db,
                self.vault_id,
                deposit_request_canceled_data['request_id'],
                event_data['event_timestamp']
            )

        self.save_to_db_batch('DepositRequestCanceled', event_data_list)

    def store_Transfer_events(self, events: List[Dict]):
        event_data_list = []
        transfer_data_list = []
        for event in events:
            event_data, transfer_data = EventFormatter.format_Transfer_data(event, self.vault_id)
            event_data_list.append(event_data)
            transfer_data_list.append(transfer_data)

        self.save_to_db_batch('events', event_data_list)
        self.save_to_db_batch('Transfer', transfer_data_list)

    def store_NewTotalAssetsUpdated_events(self, events: List[Dict]):
        event_data_list = []
        new_total_assets_updated_data_list = []
        for event in events:
            event_data, new_total_assets_updated_data = EventFormatter.format_NewTotalAssetsUpdated_data(event, self.vault_id)
            event_data_list.append(event_data)
            new_total_assets_updated_data_list.append(new_total_assets_updated_data)

        self.save_to_db_batch('events', event_data_list)
        self.save_to_db_batch('NewTotalAssetsUpdated', new_total_assets_updated_data_list)

    def store_Withdraw_events(self, events: List[Dict]):
        event_data_list = []
        return_data_list = []
        for event in events:
            event_data, return_data = EventFormatter.format_Return_data(self.db, event, self.vault_id, self.chain_id, 'withdraw')
            event_data_list.append(event_data)
            return_data_list.append(return_data)
            
            # UPDATE the matching RedeemRequest status
            LagoonEvents.update_completed_redeem(
                self.db,
                self.vault_id,
                return_data['user_id'],
                LagoonDbDateUtils.get_datetime_from_str(event_data['event_timestamp'])
            )

        self.save_to_db_batch('events', event_data_list)
        self.save_to_db_batch('Withdraw', return_data_list)

    def store_Deposit_events(self, events: List[Dict]):
        event_data_list = []
        return_data_list = []
        for event in events:
            event_data, return_data = EventFormatter.format_Return_data(self.db, event, self.vault_id, self.chain_id, 'deposit')
            event_data_list.append(event_data)
            return_data_list.append(return_data)
            
            # UPDATE the matching DepositRequest status
            LagoonEvents.update_completed_deposit(
                self.db,
                self.vault_id,
                return_data['user_id'],
                LagoonDbDateUtils.get_datetime_from_str(event_data['event_timestamp'])
            )

        self.save_to_db_batch('events', event_data_list)
        self.save_to_db_batch('Deposit', return_data_list)

# Lagoon Indexer
class LagoonIndexer:
    def __init__(self, lagoon_abi: list, chain_id: int, sleep_time: int, range: int, event_names: list, real_time: bool = True, vault_id: str = None):
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
        self.event_processor = EventProcessor(self.db, self.vault_id, self.chain_id)

    def get_block_ts(self, event: Dict) -> str:
        block_number = int(event['blockNumber'])
        block = self.blockchain.node.eth.get_block(block_number)
        ts = datetime.fromtimestamp(block['timestamp'])
        return LagoonDbDateUtils.format_timestamp(ts)

    def get_latest_block_number(self) -> int:
        return self.blockchain.getLatestBlockNumber()

    def fetch_events(self, event_name: str, from_block: int, to_block: int) -> List[Dict]:
        """
        Fetches events of specified type within the given block range.
        """
        event_obj = self.lagoon_contract.events[event_name]
        event_topic = event_abi_to_log_topic(event_obj().abi)
        logs = self.blockchain.node.eth.get_logs({
            "fromBlock": from_block,
            "toBlock": to_block,
            "address": self.lagoon,
            "topics": [event_topic]
        })
        return [event_obj().process_log(log) for log in logs]


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
                elif event_name == 'Deposit':
                    self.event_processor.store_Deposit_events(events)
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
            last_processed_block = LagoonDbUtils.get_last_processed_block(self.db, self.vault_id, self.chain_id, self.first_lagoon_block)
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
            LagoonDbUtils.update_last_processed_block(self.db, self.vault_id, self.chain_id, from_block + range_to_process)
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
