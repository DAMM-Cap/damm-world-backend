import os
import sys
from typing import Dict, Tuple
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db import Database
from db.query.lagoon_db_utils import LagoonDbUtils
from db.utils.lagoon_db_date_utils import LagoonDbDateUtils
from decimal import Decimal
from uuid import UUID, uuid5

EVENT_NAMESPACE = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

def make_event_id(vault_id: str, block_number: int, log_index: int) -> str:
    name = f"{vault_id}:{block_number}:{log_index}"
    return str(uuid5(EVENT_NAMESPACE, name))

class EventFormatter:
    @staticmethod
    def _format_Event_data(event: Dict, vault_id: str, event_type: str) -> Dict:
        block_number = int(event['blockNumber'])
        log_index = int(event['logIndex'])
        return {
            'event_id': make_event_id(vault_id, block_number, log_index),  # deterministic id to avoid constraint violation when retrying
            'vault_id': vault_id,
            'event_type': event_type,
            'block_number': block_number,
            'log_index': log_index,
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
        delta_hours, apy, management_fee, performance_fee, entrance_rate, exit_rate = LagoonDbUtils.handle_vault_snapshot(
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
            'delta_hours': delta_hours,
            'entrance_rate': entrance_rate,
            'exit_rate': exit_rate
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
        event_data = EventFormatter._format_Event_data(event, vault_id, 'deposit_canceled')
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
    
