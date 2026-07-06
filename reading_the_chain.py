import random
import json
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.providers.rpc import HTTPProvider


NOW_TOKEN = "YOUR_NOWNODES_TOKEN"
ALCHEMY_TOKEN = "YOUR_ALCHEMY_TOKEN"
INFURA_TOKEN = "YOUR_INFURA_TOKEN"

ETH_URL = f"https://eth-mainnet.alchemyapi.io/v2/{ALCHEMY_TOKEN}"
BNB_URL = f"https://bsc-testnet.nownodes.io/{NOW_TOKEN}"


def connect_to_eth():
    w3 = Web3(HTTPProvider(ETH_URL))
    assert w3.is_connected(), "Failed to connect to Ethereum mainnet"
    return w3


def connect_with_middleware(contract_json):
    w3 = Web3(HTTPProvider(BNB_URL))
    assert w3.is_connected(), "Failed to connect to BNB testnet"

    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    with open(contract_json, "r") as f:
        data = json.load(f)

    contract = w3.eth.contract(
        address=data["bsc"]["address"],
        abi=data["bsc"]["abi"]
    )

    return w3, contract


def is_ordered_block(w3, block_num):
    block = w3.eth.get_block(block_num, full_transactions=True)
    base_fee = block.get("baseFeePerGas", 0)

    fees = []

    for tx_hash in block["transactions"]:
        tx = w3.eth.get_transaction(tx_hash)

        if "maxPriorityFeePerGas" in tx:
            priority_fee = min(
                tx["maxPriorityFeePerGas"],
                tx["maxFeePerGas"] - base_fee
            )
        else:
            priority_fee = tx["gasPrice"] - base_fee

        fees.append(priority_fee)

    for i in range(len(fees) - 1):
        if fees[i] < fees[i + 1]:
            return False

    return True


def get_contract_values(contract, admin_address, owner_address):
    default_admin_role = contract.functions.DEFAULT_ADMIN_ROLE().call()

    onchain_root = contract.functions.merkleRoot().call()
    has_role = contract.functions.hasRole(default_admin_role, admin_address).call()
    prime = contract.functions.getPrimeByOwner(owner_address).call()

    return onchain_root, has_role, prime


if __name__ == "__main__":
    admin_address = "0xAC55e7d73A792fE1A9e051BDF4A010c33962809A"
    owner_address = "0x793A37a85964D96ACD6368777c7C7050F05b11dE"
    contract_file = "contract_info.json"

    eth_w3 = connect_to_eth()
    _, contract = connect_with_middleware(contract_file)

    latest_block = eth_w3.eth.get_block_number()
    london_hard_fork_block_num = 12965000
    assert latest_block > london_hard_fork_block_num

    for _ in range(5):
        block_num = random.randint(london_hard_fork_block_num + 1, latest_block)
        ordered = is_ordered_block(eth_w3, block_num)
        print(f"Block {block_num} ordered: {ordered}")

    root, role, prime = get_contract_values(
        contract, admin_address, owner_address
    )
    print("merkleRoot:", root)
    print("has_role:", role)
    print("prime:", prime)