from typing import Dict
from web3 import AsyncWeb3,Web3
from web3.middleware import async_geth_poa_middleware
import ssl
import certifi
import app.constants.addresses as addresses
from app.constants.abi.erc20 import ERC20_ABI
from app.constants.abi.lagoon import LAGOON_ABI
from app.constants.abi.weth9 import WETH9_ABI
from app.constants.abi.optimismMintableERC20 import WLD_ABI
from app.constants.abi.safe import SAFE_ABI
from app.utils.rpc import get_rpc_url
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
        return self.node.eth.contract(address=Web3.to_checksum_address(addresses.DAMM_WORLD_ADDRESSES[self.chain_id]['lagoon']),abi=LAGOON_ABI)
    
    def get_wrapped_native_weth_contract(self):
        return self.node.eth.contract(address=Web3.to_checksum_address(addresses.DAMM_WORLD_ADDRESSES[self.chain_id]['wrapped_native_weth_token']),abi=WETH9_ABI)
    
    def get_wld_contract(self):
        return self.node.eth.contract(address=Web3.to_checksum_address(addresses.DAMM_WORLD_ADDRESSES[self.chain_id]['wld_token']),abi=WLD_ABI)
    
    def get_safe_contract(self):
        return self.node.eth.contract(address=Web3.to_checksum_address(addresses.DAMM_WORLD_ADDRESSES[self.chain_id]['safe']),abi=SAFE_ABI)
    
def getEnvNode(chain_id: int) -> Blockchain:
    if chain_id == 480:
        return Blockchain(get_rpc_url(480), 480)
    elif chain_id == 31337:
        return Blockchain(get_rpc_url(31337), 31337)
    elif chain_id == 8453:
        return Blockchain(get_rpc_url(8453), 8453)
    elif chain_id == 1:
        return Blockchain(get_rpc_url(1), 1)
    else:
        raise Exception('RPC unavailable for that chain_id')
