from web3 import Web3

def get_lagoon_deployments(chain_id: int):
    deployments = {
        480: {
            "genesis_block_lagoon": 14306135,
            "lagoon_address": Web3.to_checksum_address("0x97aAC927FBe5802a23aC562699a51F0CfF23cF9A"),
            "safe_address": Web3.to_checksum_address("0x29B055022B53937E3D147D6FDFBA08aBe9A6D434"),
            "wrapped_native_weth_token": Web3.to_checksum_address("0x4200000000000000000000000000000000000006"),
            "wld_token": Web3.to_checksum_address("0x2cFc85d8E48F8EAB294be644d9E25C3030863003")
        },
        31337: {
            "genesis_block_lagoon": 14306135,
            "lagoon_address": Web3.to_checksum_address("0x97aAC927FBe5802a23aC562699a51F0CfF23cF9A"),
            "safe_address": Web3.to_checksum_address("0x29B055022B53937E3D147D6FDFBA08aBe9A6D434"),
            "wrapped_native_weth_token": Web3.to_checksum_address("0x4200000000000000000000000000000000000006"),
            "wld_token": Web3.to_checksum_address("0x2cFc85d8E48F8EAB294be644d9E25C3030863003")
        },
    }
    if chain_id not in deployments:
        raise ValueError(f"Chain ID {chain_id} not supported")
        
    return deployments[chain_id]