import json
import os
import pandas as pd
from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware  # Necessary for POA chains


def connect_to(chain):
    """
    Connect to Avalanche Fuji (source) or BNB Chain Testnet (destination)
    """
    if chain == 'source':  # The source contract chain is AVAX Fuji
        api_url = "https://api.avax-test.network/ext/bc/C/rpc"

    elif chain == 'destination':  # The destination contract chain is BSC Testnet
        api_url = "https://data-seed-prebsc-1-s1.binance.org:8545/"

    else:
        api_url = chain

    if chain in ['source', 'destination']:
        w3 = Web3(HTTPProvider(api_url))
        # Inject the POA compatibility middleware to the innermost layer
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        return w3
    
    return None


def get_contract_info(chain, contract_info_path="contract_info.json"):
    """
    Load the contract_info file into a dictionary
    """
    try:
        with open(contract_info_path, 'r') as f:
            contracts = json.load(f)
        return contracts[chain]
    except Exception as e:
        print(f"Failed to read contract info\nPlease contact your instructor\n{e}")
        return None


def get_warden_key(contract_info_path="contract_info.json"):
    """
    从 contract_info.json 或环境变量中提取 Warden（管理员）私钥
    """
    try:
        with open(contract_info_path, 'r') as f:
            data = json.load(f)
    except Exception:
        data = {}

    # 1. 检查根节点常见键名
    for key in ['secret_key', 'private_key', 'warden_private_key', 'warden_key', 'signing_key']:
        if key in data and isinstance(data[key], str):
            return data[key]

    # 2. 检查 "warden" 子字典或字符串
    if 'warden' in data:
        if isinstance(data['warden'], str):
            return data['warden']
        elif isinstance(data['warden'], dict):
            for key in ['private_key', 'secret_key', 'key', 'signing_key']:
                if key in data['warden'] and isinstance(data['warden'][key], str):
                    return data['warden'][key]

    # 3. 检查 source / destination 内嵌套的私钥
    for chain_key in ['source', 'destination']:
        if chain_key in data and isinstance(data[chain_key], dict):
            for key in ['private_key', 'secret_key', 'warden_private_key']:
                if key in data[chain_key] and isinstance(data[chain_key][key], str):
                    return data[chain_key][key]

    # 4. 检查系统环境变量
    for env_var in ['PRIVATE_KEY', 'WARDEN_PRIVATE_KEY', 'SECRET_KEY', 'WARDEN_KEY']:
        if env_var in os.environ:
            return os.environ[env_var]

    return None


def send_signed_transaction(w3, contract_function, private_key):
    """
    构建、签名并广播以太坊交易，等待 Receipt 返回
    """
    account = w3.eth.account.from_key(private_key)
    sender_address = account.address

    # 获取当前最新的 pending nonce，避免多笔交易 Nonce 冲突
    nonce = w3.eth.get_transaction_count(sender_address, 'pending')

    tx_params = {
        'from': sender_address,
        'nonce': nonce,
        'gasPrice': w3.eth.gas_price,
        'chainId': w3.eth.chain_id
    }

    # 预估 Gas 限额（带 20% 缓冲区）
    try:
        gas_estimate = contract_function.estimate_gas({'from': sender_address})
        tx_params['gas'] = int(gas_estimate * 1.2)
    except Exception:
        tx_params['gas'] = 300000  # 备用 Gas 限额

    # 构建并签名交易
    tx = contract_function.build_transaction(tx_params)
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=private_key)
    
    # 兼容 Web3.py v5 与 v6 的 rawTransaction 属性读取
    raw_tx = getattr(signed_tx, 'raw_transaction', getattr(signed_tx, 'rawTransaction', None))

    # 发送交易并等待确认
    tx_hash = w3.eth.send_raw_transaction(raw_tx)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt


def scan_blocks(chain, contract_info="contract_info.json"):
    """
    chain - (string) should be either "source" or "destination"
    Scan the last 5 blocks of the source and destination chains
    Look for 'Deposit' events on the source chain and 'Unwrap' events on the destination chain
    When Deposit events are found on the source chain, call the 'wrap' function on the destination chain
    When Unwrap events are found on the destination chain, call the 'withdraw' function on the source chain
    """

    if chain not in ['source', 'destination']:
        print(f"Invalid chain: {chain}")
        return 0

    # 1. 连接到两条链的节点
    w3_source = connect_to('source')
    w3_dest = connect_to('destination')

    # 2. 读取两链合约信息
    source_info = get_contract_info('source', contract_info)
    dest_info = get_contract_info('destination', contract_info)

    if not source_info or not dest_info:
        print("Error: Could not load contract information.")
        return 0

    # 实例化合约对象
    source_contract = w3_source.eth.contract(
        address=Web3.to_checksum_address(source_info['address']),
        abi=source_info['abi']
    )
    dest_contract = w3_dest.eth.contract(
        address=Web3.to_checksum_address(dest_info['address']),
        abi=dest_info['abi']
    )

    # 3. 获取 Warden 私钥
    private_key = get_warden_key(contract_info)
    if not private_key:
        print("Error: Warden private key not found!")
        return 0

    # 4. 根据输入的 chain 进行区块扫描与跨链响应
    if chain == 'source':
        # 扫描 Source 链 (AVAX) 最近 5 个区块的 Deposit 事件 -> 在 Destination 链 (BSC) 触发 wrap()
        latest_block = w3_source.eth.block_number
        from_block = max(0, latest_block - 4)

        deposit_events = source_contract.events.Deposit().get_logs(
            from_block=from_block,
            to_block=latest_block
        )

        for event in deposit_events:
            token = event.args.token
            recipient = event.args.recipient
            amount = event.args.amount

            print(f"[Source Event Captured] Deposit: token={token}, recipient={recipient}, amount={amount}")

            # 调用 Destination 合约的 wrap(_underlying_token, _recipient, _amount)
            wrap_func = dest_contract.functions.wrap(token, recipient, amount)
            try:
                receipt = send_signed_transaction(w3_dest, wrap_func, private_key)
                print(f" -> Successfully invoked wrap() on Destination chain! Tx: {receipt.transactionHash.hex()}")
            except Exception as e:
                print(f" -> Failed to execute wrap() on Destination: {e}")

    elif chain == 'destination':
        # 扫描 Destination 链 (BSC) 最近 5 个区块的 Unwrap 事件 -> 在 Source 链 (AVAX) 触发 withdraw()
        latest_block = w3_dest.eth.block_number
        from_block = max(0, latest_block - 4)

        unwrap_events = dest_contract.events.Unwrap().get_logs(
            from_block=from_block,
            to_block=latest_block
        )

        for event in unwrap_events:
            underlying_token = event.args.underlying_token
            recipient = event.args.to  # Unwrap 事件中的 'to' 字段对应解锁资产的目标接收者
            amount = event.args.amount

            print(f"[Destination Event Captured] Unwrap: underlying_token={underlying_token}, recipient={recipient}, amount={amount}")

            # 调用 Source 合约的 withdraw(_token, _recipient, _amount)
            withdraw_func = source_contract.functions.withdraw(underlying_token, recipient, amount)
            try:
                receipt = send_signed_transaction(w3_source, withdraw_func, private_key)
                print(f" -> Successfully invoked withdraw() on Source chain! Tx: {receipt.transactionHash.hex()}")
            except Exception as e:
                print(f" -> Failed to execute withdraw() on Source: {e}")

    return 1