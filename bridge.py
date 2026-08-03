import json
import os
import pandas as pd
from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware

BSC_RPCS = [
    "https://data-seed-prebsc-1-s1.binance.org:8545/",
    "https://bsc-testnet.publicnode.com",
    "https://data-seed-prebsc-2-s1.binance.org:8545/"
]

def connect_to(chain):
    """
    Connect to Avalanche Fuji (source) or BNB Chain Testnet (destination)
    """
    if chain == 'source':
        api_url = "https://api.avax-test.network/ext/bc/C/rpc"
        w3 = Web3(HTTPProvider(api_url))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        return w3

    elif chain == 'destination':
        for rpc in BSC_RPCS:
            try:
                w3 = Web3(HTTPProvider(rpc))
                if w3.is_connected():
                    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
                    return w3
            except Exception:
                continue
        # Fallback to default
        w3 = Web3(HTTPProvider(BSC_RPCS[0]))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        return w3

    else:
        w3 = Web3(HTTPProvider(chain))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        return w3


def get_contract_info(chain, contract_info_path="contract_info.json"):
    try:
        with open(contract_info_path, 'r') as f:
            contracts = json.load(f)
        return contracts[chain]
    except Exception as e:
        print(f"Failed to read contract info\nPlease contact your instructor\n{e}")
        return None


def get_warden_key(contract_info_path="contract_info.json"):
    try:
        with open(contract_info_path, 'r') as f:
            data = json.load(f)
    except Exception:
        data = {}

    for key in ['secret_key', 'private_key', 'warden_private_key', 'warden_key', 'signing_key']:
        if key in data and isinstance(data[key], str):
            return data[key]

    if 'warden' in data:
        if isinstance(data['warden'], str):
            return data['warden']
        elif isinstance(data['warden'], dict):
            for key in ['private_key', 'secret_key', 'key', 'signing_key']:
                if key in data['warden'] and isinstance(data['warden'][key], str):
                    return data['warden'][key]

    for chain_key in ['source', 'destination']:
        if chain_key in data and isinstance(data[chain_key], dict):
            for key in ['private_key', 'secret_key', 'warden_private_key']:
                if key in data[chain_key] and isinstance(data[chain_key][key], str):
                    return data[chain_key][key]

    for env_var in ['PRIVATE_KEY', 'WARDEN_PRIVATE_KEY', 'SECRET_KEY', 'WARDEN_KEY']:
        if env_var in os.environ:
            return os.environ[env_var]

    return None


def send_signed_transaction(w3, contract_function, private_key):
    account = w3.eth.account.from_key(private_key)
    sender_address = account.address

    nonce = w3.eth.get_transaction_count(sender_address, 'pending')

    gas_price = w3.eth.gas_price
    min_gp = w3.to_wei(25, 'gwei') if ('avax' in w3.provider.endpoint_uri or 'fuji' in w3.provider.endpoint_uri) else w3.to_wei(3, 'gwei')
    if gas_price < min_gp:
        gas_price = min_gp

    tx_params = {
        'from': sender_address,
        'nonce': nonce,
        'gasPrice': gas_price,
        'chainId': w3.eth.chain_id
    }

    try:
        gas_estimate = contract_function.estimate_gas({'from': sender_address})
        tx_params['gas'] = int(gas_estimate * 1.25)
    except Exception:
        tx_params['gas'] = 350000

    tx = contract_function.build_transaction(tx_params)
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=private_key)
    
    raw_tx = getattr(signed_tx, 'raw_transaction', getattr(signed_tx, 'rawTransaction', None))

    tx_hash = w3.eth.send_raw_transaction(raw_tx)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt


def scan_blocks(chain, contract_info="contract_info.json"):
    if chain not in ['source', 'destination']:
        print(f"Invalid chain: {chain}")
        return 0

    w3_source = connect_to('source')
    w3_dest = connect_to('destination')

    source_info = get_contract_info('source', contract_info)
    dest_info = get_contract_info('destination', contract_info)

    if not source_info or not dest_info:
        print("Error: Could not load contract information.")
        return 0

    source_contract = w3_source.eth.contract(
        address=Web3.to_checksum_address(source_info['address']),
        abi=source_info['abi']
    )
    dest_contract = w3_dest.eth.contract(
        address=Web3.to_checksum_address(dest_info['address']),
        abi=dest_info['abi']
    )

    private_key = get_warden_key(contract_info)
    if not private_key:
        print("Error: Warden private key not found!")
        return 0

    if chain == 'source':
        latest_block = w3_source.eth.block_number
        from_block = max(0, latest_block - 4)

        try:
            deposit_events = source_contract.events.Deposit().get_logs(
                from_block=from_block,
                to_block=latest_block
            )
        except Exception as e:
            print(f"Error reading Deposit logs: {e}")
            deposit_events = []

        for event in deposit_events:
            args = event.args
            token = getattr(args, 'token', getattr(args, '_token', None))
            recipient = getattr(args, 'recipient', getattr(args, '_recipient', getattr(args, 'to', None)))
            amount = getattr(args, 'amount', getattr(args, '_amount', None))

            print(f"[Source Event Captured] Deposit: token={token}, recipient={recipient}, amount={amount}")

            wrap_func = dest_contract.functions.wrap(token, recipient, amount)
            try:
                receipt = send_signed_transaction(w3_dest, wrap_func, private_key)
                print(f" -> Successfully invoked wrap() on Destination chain! Tx: {receipt.transactionHash.hex()}")
            except Exception as e:
                print(f" -> Failed to execute wrap() on Destination: {e}")

    elif chain == 'destination':
        latest_block = w3_dest.eth.block_number
        from_block = max(0, latest_block - 4)

        try:
            unwrap_events = dest_contract.events.Unwrap().get_logs(
                from_block=from_block,
                to_block=latest_block
            )
        except Exception as e:
            print(f"Error reading Unwrap logs: {e}")
            unwrap_events = []

        for event in unwrap_events:
            args = event.args
            underlying_token = getattr(args, 'underlying_token', getattr(args, '_underlying_token', getattr(args, 'token', None)))
            recipient = getattr(args, 'to', getattr(args, 'recipient', getattr(args, '_recipient', None)))
            amount = getattr(args, 'amount', getattr(args, '_amount', None))

            print(f"[Destination Event Captured] Unwrap: underlying_token={underlying_token}, recipient={recipient}, amount={amount}")

            withdraw_func = source_contract.functions.withdraw(underlying_token, recipient, amount)
            try:
                receipt = send_signed_transaction(w3_source, withdraw_func, private_key)
                print(f" -> Successfully invoked withdraw() on Source chain! Tx: {receipt.transactionHash.hex()}")
            except Exception as e:
                print(f" -> Failed to execute withdraw() on Source: {e}")

    return 1