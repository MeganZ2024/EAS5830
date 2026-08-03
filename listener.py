from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware
from pathlib import Path
import json
import pandas as pd


def scan_blocks(chain, start_block, end_block, contract_address, eventfile='deposit_logs.csv'):
    """
    chain - string (Either 'bsc' or 'avax')
    start_block - integer/string or "latest" first block to scan
    end_block - integer/string or "latest" last block to scan
    contract_address - the address of the deployed contract

    Scans specified blocks for "Deposit" events and saves them to deposit_logs.csv.
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

    # Ensure valid checksum address (Guarantees 0x prefix)
    contract_address = Web3.to_checksum_address(contract_address)

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
    
    contract = w3.eth.contract(address=contract_address, abi=DEPOSIT_ABI)

    # 4. Strictly handle string-to-int conversion for block parameters
    if start_block == "latest":
        start_block = w3.eth.get_block_number()
    else:
        start_block = int(start_block)  

    if end_block == "latest":
        end_block = w3.eth.get_block_number()
    else:
        end_block = int(end_block)

    if end_block < start_block:
        print(f"Error: end_block ({end_block}) < start_block ({start_block})!")
        return

    events_list = []

    # CRITICAL FIX: Use w3.to_hex() to ensure the 0x prefix is attached to the topic
    event_topic = w3.to_hex(w3.keccak(text="Deposit(address,address,uint256)"))

    def fetch_and_process_logs(f_block, t_block):
        # Web3.py automatically converts integer block parameters to correct 0x hex strings internally
        raw_logs = w3.eth.get_logs({
            'fromBlock': f_block,
            'toBlock': t_block,
            'address': contract_address,
            'topics': [event_topic]
        })

        for log in raw_logs:
            # Decode the raw log into event arguments
            decoded_event = contract.events.Deposit().process_log(log)
            
            # Format transaction hash safely
            if hasattr(decoded_event.transactionHash, 'hex'):
                tx_hash = decoded_event.transactionHash.hex()
            else:
                tx_hash = str(decoded_event.transactionHash)

            if not tx_hash.startswith("0x"):
                tx_hash = "0x" + tx_hash

            data = {
                'chain': chain,
                'token': decoded_event.args['token'],
                'recipient': decoded_event.args['recipient'],
                'amount': decoded_event.args['amount'],
                'transactionHash': tx_hash,
                'address': decoded_event.address
            }
            events_list.append(data)

    # 5. Fetch logs safely handling block ranges
    if end_block - start_block < 30:
        fetch_and_process_logs(start_block, end_block)
    else:
        # Prevent RPC limits by looping one by one for large ranges
        for block_num in range(start_block, end_block + 1):
            fetch_and_process_logs(block_num, block_num)

    # 6. Export to deposit_logs.csv
    csv_path = Path(eventfile)
    headers = ['chain', 'token', 'recipient', 'amount', 'transactionHash', 'address']

    if events_list:
        df = pd.DataFrame(events_list)[headers]
        
        # Append if file exists and has content; write new file with headers otherwise
        if csv_path.is_file() and csv_path.stat().st_size > 0:
            df.to_csv(eventfile, mode='a', index=False, header=False)
        else:
            df.to_csv(eventfile, mode='w', index=False, header=True)
    else:
        # Create empty template CSV with headers if no events found and file doesn't exist
        if not csv_path.is_file() or csv_path.stat().st_size == 0:
            empty_df = pd.DataFrame(columns=headers)
            empty_df.to_csv(eventfile, index=False)