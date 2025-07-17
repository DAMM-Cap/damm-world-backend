import os

headroom = int(os.getenv("INDEXER_HEADROOM", "4"))

def is_up_to_date(last_processed_block: int, current_block: int):
    return last_processed_block + headroom >= current_block

def get_block_gap(last_processed_block: int, current_block: int):
    return current_block - last_processed_block - headroom

def get_indexer_status(last_processed_block: int, latest_block: int, genesis_block_lagoon: int):
    block_gap = get_block_gap(last_processed_block, latest_block)
    percentage_behind = round((last_processed_block - genesis_block_lagoon) * 100 / (latest_block - genesis_block_lagoon), 2)
    return block_gap, percentage_behind
