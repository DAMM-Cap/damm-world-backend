def simulate_batch_transactions(w3, signed_txs):
    """
    Simulate a batch of transactions before execution.
    
    Args:
        w3: Web3 object
        signed_txs: List of signed transactions
        
    Returns:
        bool: True if simulation succeeds, False otherwise
    """
    try:
        print(f"Simulating batch: {len(signed_txs)} txs")
        
        # Simulate transactions
        for i, signed_tx in enumerate(signed_txs):
            try:
                # Decode transaction for simulation
                decoded_tx = w3.eth.account._recover_transaction(signed_tx.rawTransaction)
                print(f"Simulating tx {i+1}: {decoded_tx.hex()}")
                
                # Use eth_call for simulation (doesn't change state)
                result = w3.eth.call({
                    'to': decoded_tx['to'],
                    'data': decoded_tx['data'],
                    'from': decoded_tx['from'],
                    'gas': decoded_tx['gas'],
                    'gasPrice': decoded_tx['gasPrice'],
                    'value': decoded_tx['value']
                })
                print(f"Tx {i+1} simulation successful")
                
            except Exception as e:
                print(f"Tx {i+1} simulation failed: {e}")
                return False
        
        print("All transactions simulated successfully!")
        return True
        
    except Exception as e:
        print(f"Batch simulation failed: {e}")
        return False

def execute_batch_transactions(w3, signed_txs):
    """
    Execute a batch of transactions after successful simulation.
    
    Args:
        w3: Web3 object
        signed_txs: List of signed transactions
        
    Returns:
        list: List of transaction hashes
    """
    tx_hashes = []
    
    try:
        print(f"Executing batch: {len(signed_txs)} txs")
        
        # Execute transactions
        for i, signed_tx in enumerate(signed_txs):
            try:
                tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                print(f"Tx {i+1} sent: {tx_hash.hex()}")
                tx_hashes.append(tx_hash.hex())
                
                # Wait for confirmation
                print(f"Waiting for tx {i+1} receipt...")
                tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
                print(f"Tx {i+1} confirmed: {tx_receipt['status']}")
                
            except Exception as e:
                print(f"Tx {i+1} execution failed: {e}")
                raise
        
        print(f"Batch execution completed successfully! {len(tx_hashes)} transactions processed")
        return tx_hashes
        
    except Exception as e:
        print(f"Batch execution failed: {e}")
        raise

def process_batch_transactions(w3, signed_txs):
    """
    Process a batch of transactions with simulation first, then execution.
    
    Args:
        w3: Web3 object
        signed_txs: List of signed transactions
        
    Returns:
        list: List of transaction hashes if successful, None if simulation fails
    """
    try:
        # Step 1: Simulate all transactions
        print("=== Starting batch simulation ===")
        simulation_success = simulate_batch_transactions(w3, signed_txs)
        
        if not simulation_success:
            print("Simulation failed, aborting batch execution")
            return None
        
        # Step 2: Execute batch if simulation succeeds
        print("=== Starting batch execution ===")
        tx_hashes = execute_batch_transactions(w3, signed_txs)
        
        print("=== Batch processing completed successfully ===")
        return tx_hashes
        
    except Exception as e:
        print(f"Batch processing failed: {e}")
        raise