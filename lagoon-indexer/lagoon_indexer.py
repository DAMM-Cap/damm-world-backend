import os
import sys
import time
import random
import asyncio
import traceback
from typing import List, Dict, Tuple
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db import getEnvDb
from core.blockchain import getEnvNode
from db.query.lagoon_db_utils import LagoonDbUtils
from db.utils.lagoon_db_date_utils import LagoonDbDateUtils
from eth_utils import event_abi_to_log_topic
from utils.indexer_status import is_up_to_date, get_indexer_status

from lagoon_event_processor import EventProcessor


# -----------------------------
# Retry helper (async) with exp backoff + jitter
# -----------------------------
async def retry_async(call, *, max_attempts=6, base_delay=0.5, max_delay=6.0, jitter=0.25, on_retry=None):
    """
    call: async () -> Any
    Exponential backoff w/ jitter. Raises last error if all attempts fail.
    """
    attempt = 0
    last_exc = None
    while attempt < max_attempts:
        try:
            return await call()
        except Exception as e:
            last_exc = e
            attempt += 1
            if on_retry:
                try:
                    on_retry(attempt, e)
                except Exception:
                    pass
            if attempt >= max_attempts:
                break
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            # +/- jitter
            delay *= (1.0 + jitter * (2 * random.random() - 1))
            await asyncio.sleep(max(0.0, delay))
    raise last_exc
class LagoonIndexer:
    def __init__(self, chain_id: int, lagoon_address: str, silo_address: str, genesis_block_number: int, 
                 sleep_time: int, range: int, event_names: list, real_time: bool = True, vault_id: str = None):
        self.first_lagoon_block = genesis_block_number-1 # -1 To process the first block
        self.lagoon = lagoon_address
        self.silo = silo_address
        self.vault_id = vault_id
        self.chain_id = chain_id
        
        self.sleep_time = sleep_time
        self.range = range
        self.real_time = real_time
        self.event_names = event_names

        self.blockchain = getEnvNode(chain_id)
        self.lagoon_contract = self.blockchain.get_lagoon_contract(lagoon_address)
        self.db = getEnvDb(os.getenv('DB_NAME'))
        self.event_processor = EventProcessor(self.db, self.lagoon, self.vault_id, self.chain_id)

        self.MAX_FETCH_SPAN = int(os.getenv("MAX_FETCH_SPAN", "0"))  # RPC client fetch limit. 0 means no splitting

    def get_block_ts(self, event: Dict) -> str:
        block_number = int(event['blockNumber'])
        ts = datetime.fromtimestamp(self.blockchain.getBlockTimestamp(block_number))
        return LagoonDbDateUtils.format_timestamp(ts)

    def get_latest_block_number(self) -> int:
        return self.blockchain.getLatestBlockNumber()

    def fetch_events(self, from_block: int, to_block: int) -> List[Dict]:
        """
        Fetches events of specified type within the given block range.
        """
        try:
            event_objects = [self.lagoon_contract.events[event_name] for event_name in self.event_names]
            event_topics = [event_abi_to_log_topic(event_obj().abi) for event_obj in event_objects]
            
            # Get logs for all event topics
            logs = self.blockchain.get_logs(from_block, to_block, self.lagoon, event_topics)
            
            # Process each log with the appropriate event object
            events = []
            for log in logs:
                # Find the matching event object for this log by checking the first topic
                log_topic = log['topics'][0] if log['topics'] else None
                if not log_topic:
                    continue
                
                # Find the matching event object for this log
                for i, event_obj in enumerate(event_objects):
                    if event_topics[i] == log_topic:
                        try:
                            processed_event = event_obj().process_log(log)
                            if processed_event:
                                # Convert AttributeDict to regular dict to allow item assignment
                                event_dict = dict(processed_event)
                                event_dict['event_name'] = event_obj.event_name
                                event_dict['blockTimestamp'] = self.get_block_ts(processed_event)
                                events.append(event_dict)
                                break
                        except Exception as e:
                            print(f"Failed to process log with {event_obj.event_name}: {e}")
                            continue
            
            return events
        except Exception as e:
            print(f"Error fetching events: {e}")
            raise


    async def _fetch_events_for_type(self, from_block: int, to_block: int) -> List[Dict]:
        """
        Fetch with retries; optionally split large ranges to avoid provider limits.
        """
        async def _call():
            # optional range splitting
            if self.MAX_FETCH_SPAN and (to_block - from_block) > self.MAX_FETCH_SPAN:
                print(f"Spliting fetch range to {from_block}-{mid} and {mid + 1}-{to_block}")
                mid = from_block + (to_block - from_block) // 2
                left, right = await asyncio.gather(
                    self._fetch_events_for_type(from_block, mid),
                    self._fetch_events_for_type(mid + 1, to_block),
                )
                return left + right
            # single shot
            return await asyncio.to_thread(self.fetch_events, from_block, to_block)

        def _on_retry(attempt, err):
            print(f"[retry] attempt {attempt} failed: {err}")
            traceback.print_exc()
            # refresh provider after failures
            self.blockchain = getEnvNode(self.chain_id)

        return await retry_async(
            _call,
            max_attempts=6,
            base_delay=0.5,
            max_delay=6.0,
            jitter=0.25,
            on_retry=_on_retry
        )

    async def fetch_and_store(self, from_block: int, range: int):
        """
        Fetch events for all configured types, process them in strict chain order,
        and atomically commit both data and checkpoint in a single DB transaction.
        """
        to_block = from_block + range
        print(f"Fetching events {from_block} to {to_block} for {len(self.event_names)} types")

        # 1) concurrent fetches with retry
        tasks = [self._fetch_events_for_type(from_block, to_block)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 2) if any hard failure, abort (let fetcher_loop retry same range later)
        for r in results:
            if isinstance(r, Exception):
                raise r

        # 3) flatten + sort
        all_events: List[Dict] = [e for group in results for e in group]
        all_events.sort(key=lambda e: (int(e['blockNumber']), int(e['logIndex'])))

        # 4) ordered processing with buffered writes
        buffers: Dict[str, List[Dict]] = {event_name: [] for event_name in self.event_names}

        async def flush(name: str):
            """
            Flush one buffer through the appropriate store_* method.
            Clear only on success to keep at-least-once semantics safe.
            """
            if not buffers[name]:
                return
            batch = buffers[name][:]  # copy
            try:
                if name == 'DepositRequest':
                    await self.event_processor.store_DepositRequest_events(batch)
                elif name == 'RedeemRequest':
                    await self.event_processor.store_RedeemRequest_events(batch)
                elif name == 'SettleDeposit':
                    await self.event_processor.store_Settlement_events(batch, 'deposit')
                elif name == 'SettleRedeem':
                    await self.event_processor.store_Settlement_events(batch, 'redeem')
                elif name == 'DepositRequestCanceled':
                    await self.event_processor.store_DepositRequestCanceled_events(batch)
                elif name == 'Transfer':
                    await self.event_processor.store_Transfer_events(batch)
                elif name == 'NewTotalAssetsUpdated':
                    self.event_processor.store_NewTotalAssetsUpdated_events(batch)
                elif name == 'RatesUpdated':
                    self.event_processor.store_RatesUpdated_events(batch)
                elif name == 'Withdraw':
                    await self.event_processor.store_Withdraw_events(batch)
                elif name == 'Deposit':
                    await self.event_processor.store_Deposit_events(batch)
                elif name == 'Referral':
                    self.event_processor.store_Referral_events(batch)
                elif name == 'StateUpdated':
                    self.event_processor.store_StateUpdated_events(batch)
                elif name == 'Paused':
                    self.event_processor.store_Paused_events(batch)
                elif name == 'Unpaused':
                    self.event_processor.store_Unpaused_events(batch)
                # if success then clear
                buffers[name].clear()
            except Exception as e:
                print(f"Error flushing {name} batch: {e}")
                traceback.print_exc()
                self.blockchain = getEnvNode(self.chain_id)
                # keep buffer content for next retry

        # 5) Stage events into buffers
        for event in all_events:
            name = event['event_name']
            if name not in buffers:
                # Log and skip unknown event types
                print(f"Skipping unknown event type: {name}")
                continue
            buffers[name].append(event)
            await flush(name)

        print(f"Committed events from {from_block} to {to_block}")
        return to_block

    async def fetcher_loop(self):
        """
        Processes a single range of blocks and updates the last processed block in the DB.
        Returns 1 if up to date.
        """
        try:
            print(f"[{self.chain_id} - {self.lagoon}] Indexer running...")
            last_processed_block = LagoonDbUtils.get_last_processed_block(self.db, self.vault_id, self.first_lagoon_block)
            print(f"Last processed block: {last_processed_block}")

            latest_block = self.get_latest_block_number()
            print(f"Current chain head: {latest_block}")

            if is_up_to_date(last_processed_block, latest_block):
                print("Lagoon is up to date.")
                return 1
            
            # Get indexer status
            block_gap, percentage_behind = get_indexer_status(last_processed_block, latest_block, self.first_lagoon_block)
            print(f"Indexer is {percentage_behind}% towards completion of syncing.")
            print(f"Block gap: {block_gap}")

            # Get block range to process
            range_to_process = min(self.range, block_gap)
            from_block = last_processed_block + 1
            print(f"Processing block range {from_block} to {from_block + range_to_process}")

            # Wrap the entire operation in a transaction to ensure atomicity
            with self.db.connection.cursor() as cursor:
                try:
                    # Start transaction
                    cursor.execute("BEGIN")
                    
                    # Do NOT advance checkpoint if this raises
                    await self.fetch_and_store(from_block, range_to_process)

                    # If we got here, everything for this range has been stored successfully
                    new_last_processed_block = from_block + range_to_process
                    is_syncing = not is_up_to_date(new_last_processed_block, latest_block)
                    LagoonDbUtils.update_last_processed_block(self.db, self.vault_id, new_last_processed_block, is_syncing)
                    print(f"Updated last processed block to {new_last_processed_block} in DB.")

                    bot_last_processed_block = LagoonDbUtils.get_bot_last_processed_block(self.db, self.vault_id, self.first_lagoon_block)
                    print(f"Bot last processed block: {bot_last_processed_block}")
                    if (bot_last_processed_block <= new_last_processed_block):
                        LagoonDbUtils.update_bot_in_sync(self.db, self.vault_id)
                        print(f"Updated bot status to in sync in DB.")
                    else:
                        print(f"Indexer is {bot_last_processed_block - new_last_processed_block} blocks away towards bot syncing.")

                    # Commit the transaction
                    cursor.execute("COMMIT")
                    print(f"Transaction committed successfully for blocks {from_block} to {new_last_processed_block}")

                except Exception as e:
                    # Rollback the transaction on any error
                    cursor.execute("ROLLBACK")
                    print(f"Transaction rolled back due to error: {e}")
                    raise e

            if self.real_time and self.sleep_time > 0:
                print(f"Sleeping {self.sleep_time} seconds.")
                time.sleep(self.sleep_time)

        except Exception as e:
            print(f"Error in fetcher loop: {e}")
            traceback.print_exc()
            if self.sleep_time > 0:
                print(f"Sleeping {self.sleep_time} seconds before retrying.")
                time.sleep(self.sleep_time)
            return 1
