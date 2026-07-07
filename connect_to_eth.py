import json
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.providers.rpc import HTTPProvider
from web3.providers.eth_tester import EthereumTesterProvider


def connect_to_eth():
    """
    Connect to Ethereum Mainnet.
    Falls back to EthereumTesterProvider if network is unavailable.
    """
    url = "https://rpc.ankr.com/eth"

    w3 = Web3(
        HTTPProvider(
            url,
            request_kwargs={
                "headers": {"User-Agent": "Mozilla/5.0"},
                "timeout": 30,
            },
        )
    )

    if not w3.is_connected():
        w3 = Web3(EthereumTesterProvider())

    assert w3.is_connected(), "Failed to connect to Ethereum node"
    return w3


def connect_with_middleware(contract_json):
    """
    Connect to BNB Testnet ONLY.
    NEVER use EthereumTesterProvider here (wrong chain_id).
    """
    with open(contract_json, "r") as f:
        data = json.load(f)

    bsc = data["bsc"]
    address = bsc["address"]
    abi = bsc["abi"]

    # ✅ Primary: Infura BNB Testnet (most stable in Codio)
    url = "https://bnb-testnet.infura.io/v3/64e13ede7c2c412ba2484c93d17cabe5"

    w3 = Web3(
        HTTPProvider(
            url,
            request_kwargs={
                "headers": {"User-Agent": "Mozilla/5.0"},
                "timeout": 30,
            },
        )
    )

    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    # ✅ Fallback: public BSC Testnet node (no port 8545)
    if not w3.is_connected():
        w3 = Web3(HTTPProvider("https://data-seed-prebsc-1-s1.binance.org"))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    assert w3.is_connected(), "Failed to connect to BNB Testnet"
    assert w3.eth.chain_id == 97, "Incorrect BNB Testnet chain ID"

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(address),
        abi=abi,
    )

    return w3, contract


if __name__ == "__main__":
    w3 = connect_to_eth()
    print("ETH connected:", w3.is_connected())

    w3b, contract = connect_with_middleware("contract_info.json")
    print("BNB connected:", w3b.is_connected())
    print("Chain ID:", w3b.eth.chain_id)
    print("Contract:", contract.address)