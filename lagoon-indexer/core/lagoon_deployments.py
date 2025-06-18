from web3 import Web3

def get_lagoon_deployments(chain_id: int):
    deployments = {
        480: {
            "genesis_block_lagoon": 14360977,
            "lagoon_address": Web3.to_checksum_address("0x97aAC927FBe5802a23aC562699a51F0CfF23cF9A"),
            "safe_address": Web3.to_checksum_address("0x29B055022B53937E3D147D6FDFBA08aBe9A6D434"),
            "wrapped_native_weth_token": Web3.to_checksum_address("0x4200000000000000000000000000000000000006"),
            "wld_token": Web3.to_checksum_address("0x2cFc85d8E48F8EAB294be644d9E25C3030863003"),
            "silo": Web3.to_checksum_address("0xf66975719b750632c0d065b70cb4dea20d538966")
        },
        31337: {
            "genesis_block_lagoon": 14360977,
            "lagoon_address": Web3.to_checksum_address("0x97aAC927FBe5802a23aC562699a51F0CfF23cF9A"),
            "safe_address": Web3.to_checksum_address("0x29B055022B53937E3D147D6FDFBA08aBe9A6D434"),
            "wrapped_native_weth_token": Web3.to_checksum_address("0x4200000000000000000000000000000000000006"),
            "wld_token": Web3.to_checksum_address("0x2cFc85d8E48F8EAB294be644d9E25C3030863003"),
            "silo": Web3.to_checksum_address("0xf66975719b750632c0d065b70cb4dea20d538966")
        },
        8453: {
            "genesis_block_lagoon": 31139970,
            "lagoon_address": Web3.to_checksum_address("0x9c59AA6271f29ECfcefF4395b53a86f1d5A61ab9"),
            "safe_address": Web3.to_checksum_address("0xd271718aC457324b4F8CBeF186cc4AE167d67D9b"),
            "wrapped_native_weth_token": Web3.to_checksum_address("0x4200000000000000000000000000000000000006"),
            "wld_token": Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"),
            "silo": Web3.to_checksum_address("0x3a84d637f6079c39e3be13ae1d0843d4274789d5")
        },
        1: { # Testing Lagoon 9Summits flagship ETH vault deployed on mainnet
            "genesis_block_lagoon": 21137095,
            "lagoon_address": Web3.to_checksum_address("0x07ed467acd4ffd13023046968b0859781cb90d9b"),
            "safe_address": Web3.to_checksum_address("0xC868BFb240Ed207449Afe71D2ecC781D5E10C85C"),
            "wld_token": Web3.to_checksum_address("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"),
            "silo": Web3.to_checksum_address("0x924359b91eae607ba539ff6dab5bb914956ae624")
        }
    }
    if chain_id not in deployments:
        raise ValueError(f"Chain ID {chain_id} not supported")
        
    return deployments[chain_id]