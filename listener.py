import json
from pathlib import Path
import pandas as pd
from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware


def scan_blocks(chain, start_block, end_block, contract_address, eventfile='deposit_logs.csv'):
    """
    chain - string (Either 'bsc', 'avax' or custom RPC URL)
    start_block - integer/string or "latest"
    end_block - integer/string or "latest"
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
    w3 = Web3(HTTPProvider(api_url))
    if chain in ['avax', 'bsc']:
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    # Ensure valid checksum address
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

    # 4. Block range handling
    if start_block == "latest":
        start_block = w3.eth.block_number
    else:
        start_block = int(start_block)

    if end_block == "latest":
        end_block = w3.eth.block_number
    else:
        end_block = int(end_block)

    if end_block < start_block:
        print(f"Error: end_block ({end_block}) < start_block ({start_block})!")
        return

    events_list = []

    # 5. Fetch logs safely using chunking (Batch processing)
    CHUNK_SIZE = 2000  # 每次请求 2000 个区块，防止触发 RPC 限制，且大幅提升速度
    current_start = start_block

    while current_start <= end_block:
        current_end = min(current_start + CHUNK_SIZE - 1, end_block)

        # 换用 Web3.py 原生 Event 事件监听，无需手动 keccak 计算 Topic 或 process_log
        events = contract.events.Deposit().get_logs(
            from_block=current_start,
            to_block=current_end
        )

        for event in events:
            data = {
                'chain': chain,
                'token': event.args.token,
                'recipient': event.args.recipient,
                'amount': event.args.amount,
                'transactionHash': event.transactionHash.hex(),
                'address': event.address
            }
            events_list.append(data)

        current_start = current_end + 1

    # 6. Export to CSV
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