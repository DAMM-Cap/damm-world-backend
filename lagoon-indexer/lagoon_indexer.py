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
from decimal import Decimal
from utils.indexer_status import is_up_to_date, get_indexer_status

# Event Formatter
class EventFormatter:
    @staticmethod
    def _format_Event_data(event: Dict, vault_id: str, event_type: str) -> Dict:
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
        event_data = EventFormatter._format_Event_data(event, vault_id, 'deposit_request')
        current_event_ts = LagoonDbDateUtils.get_datetime_from_str(event_data['event_timestamp'])
        deposit_data = {
            'request_id': int(event['args']['requestId']),
            'event_id': event_data['event_id'],
            'vault_id': event_data['vault_id'],
            'user_id': LagoonDbUtils.get_user_id(db, event['args']['owner'].lower(), chain_id, current_event_ts),
            'sender_address': event['args']['sender'].lower(),
            'controller_address': event['args']['controller'].lower(),
            'referral_address': event['args'].get('referral', '').lower() if event['args'].get('referral') else None,
            'assets': Decimal(event['args']['assets']),
            'status': 'pending',
            'updated_at': event_data['event_timestamp'],
            'settled_at': None
        }
        return event_data, deposit_data

    @staticmethod
    def format_RedeemRequest_data(db: Database, event: Dict, vault_id: str, chain_id: int) -> Tuple[Dict, Dict]:
        event_data = EventFormatter._format_Event_data(event, vault_id, 'redeem_request')
        current_event_ts = LagoonDbDateUtils.get_datetime_from_str(event_data['event_timestamp'])
        redeem_data = {
            'request_id': int(event['args']['requestId']),
            'event_id': event_data['event_id'],
            'vault_id': event_data['vault_id'],
            'user_id': LagoonDbUtils.get_user_id(db, event['args']['owner'].lower(), chain_id, current_event_ts),
            'sender_address': event['args']['sender'].lower(),
            'controller_address': event['args']['controller'].lower(),
            'shares': Decimal(event['args']['shares']),
            'status': 'pending',
            'updated_at': event_data['event_timestamp'],
            'settled_at': None
        }
        return event_data, redeem_data
    
    @staticmethod
    def format_Settlement_data(db: Database, event: Dict, vault_id: str, settlement_type: str) -> Tuple[Dict, Dict]:
        event_type = 'settle_' + settlement_type
        event_data = EventFormatter._format_Event_data(event, vault_id, event_type)
        settle_data = {
            'event_id': event_data['event_id'],
            'vault_id': event_data['vault_id'],
            'settlement_type': settlement_type,
            'epoch_id': int(event['args']['epochId']),
        }
        total_assets = Decimal(event['args']['totalAssets'])
        total_shares = Decimal(event['args']['totalSupply'])
        share_price = Decimal(total_assets / total_shares) if total_shares > 0 else Decimal(0)
        current_event_ts = LagoonDbDateUtils.get_datetime_from_str(event_data['event_timestamp'])
        delta_hours, apy, management_fee, performance_fee = LagoonDbUtils.handle_vault_snapshot(
            db, 
            vault_id, 
            total_assets, 
            total_shares, 
            share_price, 
            current_event_ts
        )
        snapshot_data = {
            'event_id': event_data['event_id'],
            'vault_id': event_data['vault_id'],
            'total_assets': total_assets,
            'total_shares': total_shares,
            'share_price': share_price,
            'management_fee': management_fee,
            'performance_fee': performance_fee,
            'apy': apy,
            'delta_hours': delta_hours
        }
        return event_data, settle_data, snapshot_data

    @staticmethod
    def format_RatesUpdated_data(event: Dict, vault_id: str) -> Tuple[Dict, Dict]:
        event_data = EventFormatter._format_Event_data(event, vault_id, 'rates_updated')
        new_rate = event['args']['newRate']
        if isinstance(new_rate, (tuple, list)):
            management_rate, performance_rate = new_rate
        else:
            management_rate = Decimal(new_rate['managementRate'])
            performance_rate = Decimal(new_rate['performanceRate'])
        
        rates_updated_data = {
            'event_id': event_data['event_id'],
            'vault_id': event_data['vault_id'],
            'management_rate': management_rate,
            'performance_rate': performance_rate,
        }
        return event_data, rates_updated_data

    @staticmethod
    def format_DepositRequestCanceled_data(event: Dict, vault_id: str) -> Tuple[Dict, Dict]:
        event_data = EventFormatter._format_Event_data(event, vault_id, 'deposit_request_canceled')
        deposit_request_canceled_data = {
            'request_id': int(event['args']['requestId']),
        }
        return event_data, deposit_request_canceled_data

    @staticmethod
    def format_Transfer_data(event: Dict, vault_id: str) -> Tuple[Dict, Dict]:
        event_data = EventFormatter._format_Event_data(event, vault_id, 'transfer')
        transfer_data = {
            'event_id': event_data['event_id'],
            'vault_id': event_data['vault_id'],
            'from_address': event['args']['from'].lower(),
            'to_address': event['args']['to'].lower(),
            'amount': Decimal(event['args']['value']),
        }
        return event_data, transfer_data
    
    @staticmethod
    def format_NewTotalAssetsUpdated_data(event: Dict, vault_id: str) -> Tuple[Dict, Dict]:
        event_data = EventFormatter._format_Event_data(event, vault_id, 'total_assets_updated')
        new_total_assets_updated_data = {
            'event_id': event_data['event_id'],
            'vault_id': event_data['vault_id'],
            'total_assets': Decimal(event['args']['totalAssets'])
        }
        return event_data, new_total_assets_updated_data

    @staticmethod
    def format_Return_data(db: Database, event: Dict, vault_id: str, chain_id: int, return_type: str) -> Tuple[Dict, Dict]:
        event_data = EventFormatter._format_Event_data(event, vault_id, return_type)
        current_event_ts = LagoonDbDateUtils.get_datetime_from_str(event_data['event_timestamp'])
        return_data = {
            'event_id': event_data['event_id'],
            'vault_id': event_data['vault_id'],
            'user_id': LagoonDbUtils.get_user_id(db, event['args']['owner'].lower(), chain_id, current_event_ts),
            'return_type': return_type,
            'assets': Decimal(event['args']['assets']),
            'shares': Decimal(event['args']['shares']),
        }
        return event_data, return_data
    
    @staticmethod
    def format_Referral_data(event: Dict, vault_id: str) -> Tuple[Dict, Dict]:
        event_data = EventFormatter._format_Event_data(event, vault_id, 'referral')
        referral_data = {
            'event_id': event_data['event_id'],
            'vault_id': event_data['vault_id'],
            'referral_address': event['args']['referral'].lower(),
            'owner_address': event['args']['owner'].lower(),
            'request_id': int(event['args']['requestId']),
            'assets': Decimal(event['args']['assets'])
        }
        return event_data, referral_data
    
    @staticmethod
    def format_StateUpdated_data(event: Dict, vault_id: str) -> Tuple[Dict, Dict]:
        event_data = EventFormatter._format_Event_data(event, vault_id, 'state_updated')
        state = event['args']['state']
        if state == 0:
            state = 'open'
        elif state == 1:
            state = 'closing'
        elif state == 2:
            state = 'closed'
        state_updated_data = {
            'event_id': event_data['event_id'],
            'vault_id': event_data['vault_id'],
            'state': state
        }
        return event_data, state_updated_data
    
    @staticmethod
    def format_Paused_data(event: Dict, vault_id: str) -> Dict:
        event_data = EventFormatter._format_Event_data(event, vault_id, 'paused')
        return event_data
    
    @staticmethod
    def format_Unpaused_data(event: Dict, vault_id: str) -> Dict:
        event_data = EventFormatter._format_Event_data(event, vault_id, 'unpaused')
        return event_data
    
# Event Processor
class EventProcessor:
    def __init__(self, db: Database, lagoon: str, vault_id: str, chain_id: int):
        self.db = db
        self.lagoon = lagoon
        self.vault_id = vault_id
        self.chain_id = chain_id
        self.EVENT_TABLES = {
            'DepositRequest': 'deposit_requests',
            'Referral': 'deposit_requests',
            'RedeemRequest': 'redeem_requests',
            'SettleDeposit': 'settlements',
            'SettleRedeem': 'settlements',
            'DepositRequestCanceled': 'deposit_request_canceled',
            'Transfer': 'transfers',
            'NewTotalAssetsUpdated': 'vault_snapshots',
            'RatesUpdated': 'vaults',
            'Deposit': 'vault_returns',
            'Withdraw': 'vault_returns',
            'VaultSnapshot': 'vault_snapshots',
            'StateUpdated': 'vaults',
            'Paused': 'vaults',
            'Unpaused': 'vaults'
        }

    def save_to_db_batch(self, event_name: str, event_data_list: List[Dict]):
        if not event_data_list:
            return
        df = pd.DataFrame(event_data_list)
        table_name = 'events' if event_name == 'events' else self.EVENT_TABLES.get(event_name)

        if table_name:
            LagoonEvents.insert_lagoon_events(self.db, df, table_name)
            print(f"Saved {len(event_data_list)} {event_name} events to {table_name}.")

    async def store_DepositRequest_events(self, events: List[Dict]):
        event_rows = []
        deposit_rows = []
        tasks = []
        for event in events:
            event_data, deposit_data = EventFormatter.format_DepositRequest_data(self.db, event, self.vault_id, self.chain_id)
            event_rows.append(event_data)
            deposit_rows.append(deposit_data)
            
        self.save_to_db_batch('events', event_rows)
        self.save_to_db_batch('DepositRequest', deposit_rows)

    async def store_RedeemRequest_events(self, events: List[Dict]):
        event_rows = []
        redeem_rows = []
        for event in events:
            event_data, redeem_data = EventFormatter.format_RedeemRequest_data(self.db, event, self.vault_id, self.chain_id)
            event_rows.append(event_data)
            redeem_rows.append(redeem_data)

        self.save_to_db_batch('events', event_rows)
        self.save_to_db_batch('RedeemRequest', redeem_rows)

    async def store_Settlement_events(self, events: List[Dict], settlement_type: str):
        if settlement_type == 'deposit':
            update_func = LagoonEvents.update_settled_deposit_requests
            event_table = 'SettleDeposit'
        elif settlement_type == 'redeem':
            update_func = LagoonEvents.update_settled_redeem_requests
            event_table = 'SettleRedeem'
        else:
            raise ValueError(f"Invalid settlement type: {settlement_type}")

        event_data_list = []
        settle_data_list = []
        snapshot_data_list = []
        wallets = []
        for event in events:
            event_data, settle_data, snapshot_data = EventFormatter.format_Settlement_data(self.db, event, self.vault_id, settlement_type)
            event_data_list.append(event_data)
            settle_data_list.append(settle_data)
            snapshot_data_list.append(snapshot_data)

            # UPDATE the matching DepositRequest status
            wallets, txs_hashes = update_func(
                self.db,
                self.vault_id,
                event_data['event_timestamp']
            )

        self.save_to_db_batch('events', event_data_list)
        self.save_to_db_batch(event_table, settle_data_list)
        # INSERT a new vault_snapshot
        self.save_to_db_batch('VaultSnapshot', snapshot_data_list)

    def store_RatesUpdated_events(self, events: List[Dict]):
        event_data_list = []
        rates_updated_data_list = []
        for event in events:
            event_data, rates_updated_data = EventFormatter.format_RatesUpdated_data(event, self.vault_id)
            event_data_list.append(event_data)
            rates_updated_data_list.append(rates_updated_data)

            # UPDATE vault rates
            LagoonEvents.update_vault_rates(
                self.db,
                self.vault_id,
                rates_updated_data['management_rate'],
                rates_updated_data['performance_rate'],
                event_data['event_timestamp']
            )
        
        self.save_to_db_batch('events', event_data_list)

    async def store_DepositRequestCanceled_events(self, events: List[Dict]):
        event_data_list = []
        for event in events:
            event_data, deposit_request_canceled_data = EventFormatter.format_DepositRequestCanceled_data(event, self.vault_id)
            event_data_list.append(event_data)

            # UPDATE the matching DepositRequest status
            wallet, tx_hash = LagoonEvents.update_canceled_deposit_request(
                self.db,
                self.vault_id,
                deposit_request_canceled_data['request_id'],
                event_data['event_timestamp']
            )

        self.save_to_db_batch('events', event_data_list)

    async def store_Transfer_events(self, events: List[Dict]):
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

            # UPDATE the vault total_assets
            LagoonEvents.update_vault_total_assets(
                self.db,
                self.vault_id,
                new_total_assets_updated_data['total_assets'],
                LagoonDbDateUtils.get_datetime_from_str(event_data['event_timestamp'])
            )

        self.save_to_db_batch('events', event_data_list)

    async def store_Withdraw_events(self, events: List[Dict]):
        event_data_list = []
        return_data_list = []
        for event in events:
            event_data, return_data = EventFormatter.format_Return_data(self.db, event, self.vault_id, self.chain_id, 'withdraw')
            event_data_list.append(event_data)
            return_data_list.append(return_data)
            
            # UPDATE the matching RedeemRequest status
            wallets, txs_hashes = LagoonEvents.update_completed_redeem(
                self.db,
                self.vault_id,
                return_data['user_id'],
                LagoonDbDateUtils.get_datetime_from_str(event_data['event_timestamp'])
            )

        self.save_to_db_batch('events', event_data_list)
        self.save_to_db_batch('Withdraw', return_data_list)

    async def store_Deposit_events(self, events: List[Dict]):
        event_data_list = []
        return_data_list = []
        for event in events:
            event_data, return_data = EventFormatter.format_Return_data(self.db, event, self.vault_id, self.chain_id, 'deposit')
            event_data_list.append(event_data)
            return_data_list.append(return_data)
            
            # UPDATE the matching DepositRequest status
            wallets, txs_hashes = LagoonEvents.update_completed_deposit(
                self.db,
                self.vault_id,
                return_data['user_id'],
                LagoonDbDateUtils.get_datetime_from_str(event_data['event_timestamp'])
            )

        self.save_to_db_batch('events', event_data_list)
        self.save_to_db_batch('Deposit', return_data_list)
    
    def store_Referral_events(self, events: List[Dict]):
        event_data_list = []
        deposit_request_referral_data_list = []
        for event in events:
            event_data, referral_data = EventFormatter.format_Referral_data(event, self.vault_id)
            event_data_list.append(event_data)
            deposit_request_referral_data_list.append(referral_data)

            # UPDATE the matching DepositRequest referral address
            current_event_ts = LagoonDbDateUtils.get_datetime_from_str(event_data['event_timestamp'])
            LagoonEvents.update_deposit_request_referral(
                self.db,
                self.vault_id,
                LagoonDbUtils.get_user_id(self.db, referral_data['owner_address'].lower(), self.chain_id, current_event_ts),
                referral_data['referral_address']
            )

        self.save_to_db_batch('events', event_data_list)

    def store_StateUpdated_events(self, events: List[Dict]):
        event_data_list = []
        for event in events:
            event_data, state_updated_data = EventFormatter.format_StateUpdated_data(event, self.vault_id)
            event_data_list.append(event_data)

            # UPDATE the vault status
            LagoonEvents.update_vault_status(
                self.db,
                self.vault_id,
                state_updated_data['state'],
                LagoonDbDateUtils.get_datetime_from_str(event_data['event_timestamp'])
            )

        self.save_to_db_batch('events', event_data_list)

    def store_Paused_events(self, events: List[Dict]):
        event_data_list = []
        for event in events:
            event_data = EventFormatter.format_Paused_data(event, self.vault_id)
            event_data_list.append(event_data)

            # UPDATE the vault status
            LagoonEvents.update_vault_status(
                self.db,
                self.vault_id,
                'paused',
                LagoonDbDateUtils.get_datetime_from_str(event_data['event_timestamp'])
            )
        self.save_to_db_batch('events', event_data_list)

    def store_Unpaused_events(self, events: List[Dict]):
        event_data_list = []
        for event in events:
            event_data = EventFormatter.format_Unpaused_data(event, self.vault_id)
            event_data_list.append(event_data)

            # UPDATE the vault status
            LagoonEvents.update_vault_status(
                self.db,
                self.vault_id,
                'open',
                LagoonDbDateUtils.get_datetime_from_str(event_data['event_timestamp'])
            )
        self.save_to_db_batch('events', event_data_list)


# Lagoon Indexer
class LagoonIndexer:
    def __init__(self, lagoon_abi: list, chain_id: int, sleep_time: int, range: int, event_names: list, real_time: bool = True, vault_id: str = None):
        lagoon_deployments = get_lagoon_deployments(chain_id)
        self.first_lagoon_block = lagoon_deployments['genesis_block_lagoon']-1 # -1 To process the first block
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
        self.db = getEnvDb(os.getenv('DB_NAME'))
        self.event_processor = EventProcessor(self.db, self.lagoon, self.vault_id, self.chain_id)

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


    async def fetch_and_store(self, from_block: int, range: int):
        """
        Fetches and stores events for all configured event types.
        """
        to_block = from_block + range
        all_events = []

        # 1) Collect events of all types
        for event_name in self.event_names:
            try:
                print(f"Fetching {event_name} events from block {from_block} to {to_block}")
                events = self.fetch_events(event_name, from_block, to_block)
                if not events:
                    continue

                for event in events:
                    event_copy = dict(event)
                    event_copy['event_name'] = event_name  # track type
                    event_copy['blockTimestamp'] = self.get_block_ts(event)
                    all_events.append(event_copy)

            except Exception as e:
                print(f"Error fetching {event_name} events: {e}")
                traceback.print_exc()
                time.sleep(5)
                self.blockchain = getEnvNode(self.chain_id)

        # 2) Sort all events by blockNumber and logIndex
        all_events.sort(key=lambda e: (int(e['blockNumber']), int(e['logIndex'])))

        # 3) Process each event in order
        for event in all_events:
            try:
                event_name = event['event_name']
                if event_name == 'DepositRequest':
                    await self.event_processor.store_DepositRequest_events([event])
                elif event_name == 'RedeemRequest':
                    await self.event_processor.store_RedeemRequest_events([event])
                elif event_name == 'SettleDeposit':
                    await self.event_processor.store_Settlement_events([event], 'deposit')
                elif event_name == 'SettleRedeem':
                    await self.event_processor.store_Settlement_events([event], 'redeem')
                elif event_name == 'DepositRequestCanceled':
                    await self.event_processor.store_DepositRequestCanceled_events([event])
                elif event_name == 'Transfer':
                    await self.event_processor.store_Transfer_events([event])
                elif event_name == 'NewTotalAssetsUpdated':
                    self.event_processor.store_NewTotalAssetsUpdated_events([event])
                elif event_name == 'RatesUpdated':
                    self.event_processor.store_RatesUpdated_events([event])
                elif event_name == 'Withdraw':
                    await self.event_processor.store_Withdraw_events([event])
                elif event_name == 'Deposit':
                    await self.event_processor.store_Deposit_events([event])
                elif event_name == 'Referral':
                    self.event_processor.store_Referral_events([event])
                elif event_name == 'StateUpdated':
                    self.event_processor.store_StateUpdated_events([event])
                elif event_name == 'Paused':
                    self.event_processor.store_Paused_events([event])
                elif event_name == 'Unpaused':
                    self.event_processor.store_Unpaused_events([event])
            except Exception as e:
                print(f"Error processing {event['event_name']} event: {e}")
                traceback.print_exc()
                time.sleep(5)
                self.blockchain = getEnvNode(self.chain_id)

    async def fetcher_loop(self):
        """
        Processes a single range of blocks and updates the last processed block in the DB.
        Returns 1 if up to date.
        """
        try:
            last_processed_block = LagoonDbUtils.get_last_processed_block(self.db, self.vault_id, self.chain_id, self.first_lagoon_block)
            print(f"Last processed block: {last_processed_block}")

            latest_block = self.get_latest_block_number()
            print(f"Current chain head: {latest_block}")

            if is_up_to_date(last_processed_block, latest_block):
                print("Lagoon is up to date.")
                return 1
            
            # Get indexer status
            block_gap, percentage_behind = get_indexer_status(last_processed_block, latest_block, self.chain_id)
            print(f"Indexer is {percentage_behind}% towards completion of syncing.")
            print(f"Block gap: {block_gap}")

            # Get block range to process
            range_to_process = min(self.range, block_gap)
            from_block = last_processed_block + 1
            print(f"Processing block range {from_block} to {from_block + range_to_process}")

            await self.fetch_and_store(from_block, range_to_process)
            new_last_processed_block = from_block + range_to_process
            is_syncing = not is_up_to_date(new_last_processed_block, latest_block)
            LagoonDbUtils.update_last_processed_block(self.db, self.vault_id, self.chain_id, new_last_processed_block, is_syncing)
            print(f"Updated last processed block to {new_last_processed_block} in DB.")

            bot_last_processed_block = LagoonDbUtils.get_bot_last_processed_block(self.db, self.vault_id, self.chain_id, self.first_lagoon_block)
            print(f"Bot last processed block: {bot_last_processed_block}")
            if (bot_last_processed_block <= new_last_processed_block):
                LagoonDbUtils.update_bot_in_sync(self.db, self.vault_id, self.chain_id)
                print(f"Updated bot status to in sync in DB.")
            else:
                print(f"Indexer is {bot_last_processed_block - new_last_processed_block} blocks away towards bot syncing.")

            if self.real_time and self.sleep_time > 0:
                print(f"Sleeping {self.sleep_time} seconds.")
                time.sleep(self.sleep_time)

        except Exception as e:
            print(f"Error in fetcher loop: {e}")
            traceback.print_exc()
            print(f"Sleeping {self.sleep_time} seconds before retrying.")
            time.sleep(self.sleep_time)
            return 1
