from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware
from pathlib import Path
import json
import pandas as pd


def scan_blocks(chain, start_block, end_block, contract_address, eventfile='deposit_logs.csv'):
    """
    chain - string (Either 'bsc' or 'avax')
    start_block - integer or "latest" first block to scan
    end_block - integer or "latest" last block to scan
    contract_address - the address of the deployed contract

    This function reads "Deposit" events using get_logs() with snake_case parameters.
    """
    # 1. Network RPC Configuration
    if chain == 'avax':
        api_url = "https://api.avax-test.network/ext/bc/C/rpc"
    elif chain == 'bsc':
        api_url = "https://data-seed-prebsc-1-s1.binance.org:8545/"
    else:
        api_url = chain

    # 2. Web3 Connection & Middleware setup
    w3 = Web3(Web3.HTTPProvider(api_url))
    if chain in ['avax', 'bsc']:
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    # 3. Contract setup
    DEPOSIT_ABI = json.loads(
        '['
        '  {'
        '    "anonymous": false,'
        '    "inputs": ['
        '      { "indexed": true, "internalType": "address", "name": "token", "type": "address" },'
        '      { "indexed": true, "internalType": "address", "name": "recipient", "type": "address" },'
        '      { "indexed": false, "internalType": "uint256", "name": "amount", "type": "uint256" }'
        '    ],'
        '    "name": "Deposit",'
        '    "type": "event"'
        '  }'
        ']'
    )
    
    checksum_contract_address = Web3.to_checksum_address(contract_address)
    contract = w3.eth.contract(address=checksum_contract_address, abi=DEPOSIT_ABI)

    # Handle "latest" block specifications
    if start_block == "latest":
        start_block = w3.eth.get_block_number()
    if end_block == "latest":
        end_block = w3.eth.get_block_number()

    if end_block < start_block:
        print(f"Error: end_block < start_block!")
        print(f"end_block = {end_block}")
        print(f"start_block = {start_block}")
        return

    if start_block == end_block:
        print(f"Scanning block {start_block} on {chain}")
    else:
        print(f"Scanning blocks {start_block} - {end_block} on {chain}")

    events_list = []

    # Helper function to parse log entries
    def process_events(events):
        for evt in events:
            # Standardize transaction hash
            if hasattr(evt.transactionHash, 'hex'):
                tx_hash = evt.transactionHash.hex()
            else:
                tx_hash = str(evt.transactionHash)

            if not tx_hash.startswith("0x"):
                tx_hash = "0x" + tx_hash

            data = {
                'chain': chain,
                'token': evt.args['token'],
                'recipient': evt.args['recipient'],
                'amount': evt.args['amount'],
                'transactionHash': tx_hash,
                'address': evt.address
            }
            events_list.append(data)

    # 4. Fetch events using get_logs() with snake_case arguments
    if end_block - start_block < 30:
        events = contract.events.Deposit.get_logs(from_block=start_block, to_block=end_block)
        process_events(events)
    else:
        for block_num in range(start_block, end_block + 1):
            events = contract.events.Deposit.get_logs(from_block=block_num, to_block=block_num)
            process_events(events)

    # 5. Export to deposit_logs.csv
    csv_path = Path(eventfile)
    headers = ['chain', 'token', 'recipient', 'amount', 'transactionHash', 'address']

    if events_list:
        df = pd.DataFrame(events_list)[headers]
        
        if csv_path.is_file() and csv_path.stat().st_size > 0:
            df.to_csv(eventfile, mode='a', index=False, header=False)
        else:
            df.to_csv(eventfile, mode='w', index=False, header=True)
    else:
        if not csv_path.is_file() or csv_path.stat().st_size == 0:
            empty_df = pd.DataFrame(columns=headers)
            empty_df.to_csv(eventfile, index=False)