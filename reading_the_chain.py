import random
import json
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.providers.rpc import HTTPProvider

# Active API Credentials embedded directly into your configuration parameters
NOW_TOKEN = "da841d57-8091-4369-9835-62432c912a2e"
ALCHEMY_TOKEN = "YOUR_ALCHEMY_TOKEN"
INFURA_TOKEN = "64e13ede7c2c412ba2484c93d17cabe5"

# Unified Node URL Infrastructure using your provided working keys
ETH_URL = f"https://mainnet.infura.io/v3/{INFURA_TOKEN}"
BNB_URL = f"https://bsc-testnet.nownodes.io/{NOW_TOKEN}"


def connect_to_eth():
    """Establishes connection to the Ethereum Mainnet via Infura."""
    w3 = Web3(HTTPProvider(ETH_URL))
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
    Returns True if sorted descendingly, otherwise False.
    """
    # 1. Fetch block structure without full transactions to match 'get_transaction' specification requirements
    block = w3.eth.get_block(block_num, full_transactions=False)
    base_fee = block.get("baseFeePerGas", 0)

    fees = []

    # 2. Iterate over transaction hashes and compute effective miner tips
    for tx_hash in block["transactions"]:
        tx = w3.eth.get_transaction(tx_hash)

        # Evaluate EIP-1559 Type-2 Transaction state parameters
        if "maxPriorityFeePerGas" in tx and tx["maxPriorityFeePerGas"] is not None:
            priority_fee = min(
                tx["maxPriorityFeePerGas"],
                tx["maxFeePerGas"] - base_fee
            )
        else:
            # Fallback for Type-0 Legacy Transactions (GasPrice - BaseFee)
            priority_fee = tx["gasPrice"] - base_fee

        fees.append(priority_fee)

    # 3. Verify monotonic strict descending alignment matching a greedy packing sequence
    for i in range(len(fees) - 1):
        if fees[i] < fees[i + 1]:
            return False

    return True


def get_contract_values(contract, admin_address, owner_address):
    """Fetches system parameters, administration roles, and assigned primes from the target contract."""
    # Convert addresses to standard checksum variants to prevent runtime EvmAddress format errors
    admin_checksum = Web3.to_checksum_address(admin_address)
    owner_checksum = Web3.to_checksum_address(owner_address)

    # 1. Request RBAC identifier hash string
    default_admin_role = contract.functions.DEFAULT_ADMIN_ROLE().call()

    # 2. Retrieve root hash values
    onchain_root = contract.functions.merkleRoot().call()
    
    # 3. Evaluate conditional authorization mapping states
    has_role = contract.functions.hasRole(default_admin_role, admin_checksum).call()
    
    # 4. Map owner registry entries
    prime = contract.functions.getPrimeByOwner(owner_checksum).call()

    return onchain_root, has_role, prime


if __name__ == "__main__":
    # Pre-configured test validation data
    admin_address = "0xAC55e7d73A792fE1A9e051BDF4A010c33962809A"
    owner_address = "0x793A37a85964D96ACD6368777c7C7050F05b11dE"
    contract_file = "contract_info.json"

    # Runtime initialization protocols
    eth_w3 = connect_to_eth()
    _, bsc_contract = connect_with_middleware(contract_file)

    # EIP-1559 Post-Hardfork block boundary assurance rule
    latest_block = eth_w3.eth.get_block_number()
    london_hard_fork_block_num = 12965000
    assert latest_block > london_hard_fork_block_num

    # Perform greedy ordering calculation loops over random historical blocks
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