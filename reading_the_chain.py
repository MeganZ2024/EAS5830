import random
import json
import time
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.providers.rpc import HTTPProvider
from web3.exceptions import Web3RPCError

# Active API Credentials 
NOW_TOKEN = "da841d57-8091-4369-9835-62432c912a2e"
ALCHEMY_TOKEN = "YOUR_ALCHEMY_TOKEN"
INFURA_TOKEN = "64e13ede7c2c412ba2484c93d17cabe5"

# Unified Node URL Infrastructure
ETH_URL = f"https://mainnet.infura.io/v3/{INFURA_TOKEN}"
BNB_URL = "https://bsc-testnet-rpc.publicnode.com"


def connect_to_eth():
    """Establishes connection to the Ethereum Mainnet via Infura."""
    w3 = Web3(HTTPProvider(ETH_URL))
    if not w3.is_connected():
        # Fallback to public node if Infura is heavily rate-limited at connection time
        w3 = Web3(HTTPProvider("https://rpc.ankr.com/eth"))
    assert w3.is_connected(), "Failed to connect to Ethereum mainnet"
    return w3


def connect_with_middleware(contract_json):
    """Establishes connection to BNB Testnet and instantiates the contract instance."""
    w3 = Web3(HTTPProvider(BNB_URL))
    assert w3.is_connected(), "Failed to connect to BNB testnet"

    # Injecting PoA Middleware is strict for BNB Chain ecosystem compatibility
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    with open(contract_json, "r") as f:
        data = json.load(f)

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(data["bsc"]["address"]),
        abi=data["bsc"]["abi"]
    )

    return w3, contract


def is_ordered_block(w3, block_num):
    """
    Checks if a block's transactions are greedily ordered by internal priority fees.
    Includes explicit rate-limit handling for 429 errors.
    """
    # Fetch block structure without full transactions
    block = w3.eth.get_block(block_num, full_transactions=False)
    base_fee = block.get("baseFeePerGas", 0)

    fees = []

    # Iterate over transaction hashes and compute effective miner tips
    for tx_hash in block["transactions"]:
        tx = None
        retries = 5
        
        while retries > 0:
            try:
                tx = w3.eth.get_transaction(tx_hash)
                break
            except Exception as e:
                # Catch rate limits (429) or connection drops
                error_str = str(e)
                if "429" in error_str or "Too Many Requests" in error_str:
                    time.sleep(1.5)  # Wait for 1.5 seconds before retrying
                    retries -= 1
                else:
                    raise e  # Propagate other genuine exceptions

        # Fallback to prevent crashes if a transaction retrieval completely fails
        if tx is None:
            continue

        # Evaluate EIP-1559 Type-2 Transaction state parameters
        if "maxPriorityFeePerGas" in tx and tx["maxPriorityFeePerGas"] is not None:
            priority_fee = min(
                tx["maxPriorityFeePerGas"],
                tx["maxFeePerGas"] - base_fee
            )
        else:
            # Fallback for Type-0 Legacy Transactions
            priority_fee = tx["gasPrice"] - base_fee

        fees.append(priority_fee)

    # Verify monotonic strict descending alignment
    for i in range(len(fees) - 1):
        if fees[i] < fees[i + 1]:
            return False

    return True


def get_contract_values(contract, admin_address, owner_address):
    """Fetches system parameters, administration roles, and assigned primes from the target contract."""
    admin_checksum = Web3.to_checksum_address(admin_address)
    owner_checksum = Web3.to_checksum_address(owner_address)

    default_admin_role = contract.functions.DEFAULT_ADMIN_ROLE().call()
    onchain_root = contract.functions.merkleRoot().call()
    has_role = contract.functions.hasRole(default_admin_role, admin_checksum).call()
    prime = contract.functions.getPrimeByOwner(owner_checksum).call()

    return onchain_root, has_role, prime


if __name__ == "__main__":
    admin_address = "0xAC55e7d73A792fE1A9e051BDF4A010c33962809A"
    owner_address = "0x793A37a85964D96ACD6368777c7C7050F05b11dE"
    contract_file = "contract_info.json"

    eth_w3 = connect_to_eth()
    _, bsc_contract = connect_with_middleware(contract_file)

    latest_block = eth_w3.eth.get_block_number()
    london_hard_fork_block_num = 12965000
    assert latest_block > london_hard_fork_block_num

    print("--- Executing Part 1: Block Ordering Checks ---")
    for _ in range(5):
        random_block = random.randint(london_hard_fork_block_num + 1, latest_block)
        is_ordered = is_ordered_block(eth_w3, random_block)
        print(f"Block {random_block} Ordered Greedily: {is_ordered}")

    print("\n--- Executing Part 2: On-chain State Reads ---")
    root, role, prime_val = get_contract_values(
        bsc_contract, admin_address, owner_address
    )
    print("merkleRoot:", root if isinstance(root, str) else root.hex())
    print("has_role:", role)
    print("prime:", prime_val)