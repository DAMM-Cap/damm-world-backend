from typing import Dict
from web3 import AsyncWeb3,Web3
from web3.middleware import async_geth_poa_middleware
import os
import ssl
import certifi
from typing import List


import json

with open("abi/ERC20_ABI.json") as f:
    ERC20_ABI = json.load(f)

with open("abi/LAGOON_ABI.json") as f:
    LAGOON_ABI = json.load(f)

with open("abi/WETH9_ABI.json") as f:
    WETH9_ABI = json.load(f)

with open("abi/WLD_ABI.json") as f:
    WLD_ABI = json.load(f)

with open("abi/SAFE_ABI.json") as f:
    SAFE_ABI = json.load(f)

with open("abi/DAMM_WORLD_ADDRESSES.json") as f:
    DAMM_WORLD_ADDRESSES = json.load(f)


class Blockchain:

    def __init__(self,rpc_url,chain_id,is_PoA=False):
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        provider = AsyncWeb3.AsyncHTTPProvider(rpc_url, request_kwargs={"ssl": ssl_context})
        self.node=AsyncWeb3(provider)
        if is_PoA:
            self.node.middleware_onion.inject(async_geth_poa_middleware,layer=0)
        self.chain_id=chain_id
    
    async def getBlockTimestamp(self,block_num:int)->int:
        block=await self.node.eth.get_block(block_num)
        return block['timestamp']
    
    async def getLatestBlockNumber(self)->int:
        block=await self.node.eth.get_block('latest')
        return block.number
    
    async def getTxReceipt(self,tx_hash:str)->Dict:
        return await self.node.eth.get_transaction_receipt(tx_hash)
    
    async def getTxBlock(self,tx_hash:str)->int:
        receipt=await self.getTxReceipt(tx_hash)
        return receipt['blockNumber']
    
    async def getGasPrice(self)->int:
        """
        returns the current gas price in wei
        """
        return await self.node.eth.gas_price

        
    def get_function_abi(self,contract, function_name):
        for entry in contract.abi:
            if entry['type'] == 'function' and entry['name'] == function_name:
                return entry
        raise ValueError(f"Function '{function_name}' not found in contract ABI.")
        
    def get_abi_type(self,output):
        """Recursively build ABI type string for tuples and basic types."""
        if output['type'] == 'tuple':
            components = output.get('components', [])
            component_types = [self.get_abi_type(c) for c in components]
            return f"({','.join(component_types)})"
        else:
            return output['type']

    def decode_output_from_abi(self, function_abi, output_data):
        """
        Decode raw output bytes using a function ABI.
        Supports nested tuples.
        """

        # Build ABI type list from function ABI
        abi_types = [self.get_abi_type(output) for output in function_abi['outputs']]
        # Decode using web3 codec
        decode_return=self.node.eth.codec.decode(abi_types, output_data[1])
        if len(decode_return)==1:
            return decode_return[0]
        else:
            return decode_return


    def get_erc20_contract(self,address:str):
        return self.node.eth.contract(address=Web3.to_checksum_address(address),abi=ERC20_ABI)
    
    def get_lagoon_contract(self):
        return self.node.eth.contract(address=Web3.to_checksum_address(DAMM_WORLD_ADDRESSES[self.chain_id]['lagoon']),abi=LAGOON_ABI)
    
    def get_wrapped_native_weth_contract(self):
        return self.node.eth.contract(address=Web3.to_checksum_address(DAMM_WORLD_ADDRESSES[self.chain_id]['wrapped_native_weth_token']),abi=WETH9_ABI)
    
    def get_wld_contract(self):
        return self.node.eth.contract(address=Web3.to_checksum_address(DAMM_WORLD_ADDRESSES[self.chain_id]['wld_token']),abi=WLD_ABI)
    
    def get_safe_contract(self):
        return self.node.eth.contract(address=Web3.to_checksum_address(DAMM_WORLD_ADDRESSES[self.chain_id]['safe']),abi=SAFE_ABI)
    
def getEnvNode(chain_id:int)->Blockchain:
    if chain_id==480:
        return getEnvWorldchainNode()
    else:
        raise Exception('RPC unavailable for that chain_id')

def getEnvWorldchainNode():
    return Blockchain(os.getenv('WORLDCHAIN_JSON_RPC'),480)

def getEnvAnvilForkedWCNode():
    return Blockchain(os.getenv('ANVIL_FORKED_WC_JSON_RPC'),31337)