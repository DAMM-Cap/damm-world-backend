import os
import sys
import pandas as pd
from typing import List, Dict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db import Database
from db.query.lagoon_db_utils import LagoonDbUtils
from db.query.lagoon_events import LagoonEvents
from db.utils.lagoon_db_date_utils import LagoonDbDateUtils
from lagoon_event_formatter import EventFormatter

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
            'DepositRequestCanceled': 'deposit_canceled',
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

            """ if state_updated_data['state'] == 'closed':
                # UPDATE the corresponding vault on factory table's continue_indexing to False
                # This will stop the indexer from keeping indexing this vault (stopping the corresponding bot as well)
                LagoonEvents.update_vault_continue_indexing(
                    self.db,
                    self.lagoon,
                    self.chain_id,
                    False
                ) """

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

