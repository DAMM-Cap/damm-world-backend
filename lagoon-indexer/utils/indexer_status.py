headroom = 1

def is_up_to_date(last_processed_block: int, current_block: int):
    return last_processed_block + headroom >= current_block

def get_block_gap(last_processed_block: int, current_block: int):
    return current_block - last_processed_block - headroom