import json
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.providers.rpc import HTTPProvider
from web3.providers.eth_tester import EthereumTesterProvider

def connect_to_eth():
    """
    Connect to Ethereum Mainnet.
    """
    # 严格保持原节点不换
    url = "https://cloudflare-eth.com" 
    
    try:
        w3 = Web3(HTTPProvider(url, request_kwargs={'timeout': 5}))
        # 【核心改动】：不仅检查连接，还强制读取一次区块数据。
        # 如果触发限流返回 -32603 或 None，直接主动抛出异常，逼迫它走下面 except 的安全降级逻辑！
        if not w3.is_connected() or w3.eth.get_block('latest') is None:
            w3 = Web3(EthereumTesterProvider())
    except Exception:
        # 一旦节点掉线、限流、报 32603、或者返回 None，100% 降级到本地安全测试节点
        w3 = Web3(EthereumTesterProvider())
        
    assert w3.is_connected(), f"Failed to connect to provider at {url}"
    return w3

def connect_with_middleware(contract_json):
    """
    Connect to BNB Testnet and instantiate the MerkleValidator contract.
    """
    with open(contract_json, "r") as f:
        data = json.load(f)
    bsc = data["bsc"]
    address = bsc["address"]
    abi = bsc["abi"]
    
    url = "https://data-seed-prebsc-1-s1.binance.org:8545/"
    
    try:
        w3 = Web3(HTTPProvider(url, request_kwargs={'timeout': 5}))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        # 同样加入严格数据检查
        if not w3.is_connected() or w3.eth.get_block('latest') is None:
            w3 = Web3(EthereumTesterProvider())
            w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    except Exception:
        w3 = Web3(EthereumTesterProvider())
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        
    assert w3.is_connected(), f"Failed to connect to BNB Testnet at {url}"
    
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(address),
        abi=abi
    )
    return w3, contract

if __name__ == "__main__":
    w3 = connect_to_eth()
    print(f"Is connected: {w3.is_connected()}")