import json, os, sys, subprocess
from web3 import Web3

try:
    from solcx import compile_standard, install_solc
    SOLCX_AVAILABLE = True
except ImportError:
    SOLCX_AVAILABLE = False

FUJI_RPC = "https://api.avax-test.network/ext/bc/C/rpc"
BSC_TESTNET_RPC = "https://data-seed-prebsc-1-s1.binance.org:8545/"

def find_sol_file(filename):
    if os.path.exists(filename):
        return filename
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.lower() == filename.lower():
                return os.path.join(root, file)
    print(f"Error: Could not find {filename}")
    sys.exit(1)

def ensure_openzeppelin():
    target_dir = "openzeppelin-contracts"
    if not os.path.exists(target_dir):
        print("Cloning OpenZeppelin v4.9.3 via Git...")
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", "v4.9.3",
                 "https://github.com/OpenZeppelin/openzeppelin-contracts.git", target_dir],
                check=True
            )
        except Exception as e:
            print(f"Git clone error: {e}")
            sys.exit(1)

def load_config():
    with open("contract_info.json", "r") as f:
        return json.load(f)

def save_config(config):
    with open("contract_info.json", "w") as f:
        json.dump(config, f, indent=2)
    print("✓ contract_info.json updated successfully!")

def compile_solidity_file(sol_filename, contract_name, solc_version="0.8.17"):
    real_path = find_sol_file(sol_filename)
    print(f"Found {sol_filename} at: {real_path}")
    with open(real_path, "r") as f:
        source_code = f.read()
    if SOLCX_AVAILABLE:
        try:
            install_solc(solc_version)
        except Exception:
            pass
        compiled_sol = compile_standard(
            {
                "language": "Solidity",
                "sources": {real_path: {"content": source_code}},
                "settings": {
                    "remappings": [
                        "@openzeppelin/contracts/=openzeppelin-contracts/contracts/"
                    ],
                    "outputSelection": {"*": {"*": ["abi", "evm.bytecode"]}}
                },
            },
            solc_version=solc_version,
            allow_paths=".",
            base_path="."
        )
        contract_data = compiled_sol["contracts"][real_path][contract_name]
        return contract_data["abi"], contract_data["evm"]["bytecode"]["object"]
    else:
        print("solcx not available.")
        sys.exit(1)

def build_constructor_tx(Contract, admin_addr, tx_params):
    constructor_abi = [item for item in Contract.abi if item.get('type') == 'constructor']
    if not constructor_abi or len(constructor_abi[0].get('inputs', [])) == 0:
        return Contract.constructor().build_transaction(tx_params)
    
    inputs = constructor_abi[0].get('inputs', [])
    args = [admin_addr for _ in inputs]
    return Contract.constructor(*args).build_transaction(tx_params)

def deploy_contract(rpc_url, private_key, abi, bytecode, chain_name):
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print(f"Error: Could not connect to {chain_name} RPC")
        sys.exit(1)
    
    chain_id = w3.eth.chain_id
    account = w3.eth.account.from_key(private_key)
    admin_addr = account.address
    print(f"Deployer Address: {admin_addr} on {chain_name} (ChainID: {chain_id})")
    
    balance = w3.eth.get_balance(admin_addr)
    print(f"Balance: {w3.from_wei(balance, 'ether')} native tokens")

    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    gas_price = w3.eth.gas_price
    min_gas_price = w3.to_wei(25, 'gwei') if ('avax' in rpc_url or 'fuji' in rpc_url) else w3.to_wei(3, 'gwei')
    if gas_price < min_gas_price:
        gas_price = min_gas_price

    tx_params = {
        'from': admin_addr,
        'nonce': w3.eth.get_transaction_count(admin_addr),
        'chainId': chain_id,
        'gasPrice': gas_price,
    }
    
    tx = build_constructor_tx(Contract, admin_addr, tx_params)
    
    try:
        estimated_gas = w3.eth.estimate_gas(tx)
        tx['gas'] = int(estimated_gas * 1.15)
        print(f"Estimated Gas: {estimated_gas}")
    except Exception as e:
        print(f"Gas estimation note: {e}")
        tx['gas'] = 1200000

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Deploying to {chain_name}... Tx: {tx_hash.hex()}")
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"✓ Deployed {chain_name} Contract at: {tx_receipt.contractAddress}")
    return tx_receipt.contractAddress

def main():
    ensure_openzeppelin()
    config = load_config()
    private_key = config.get("secret_key")
    print("\n--- 1. Compiling Contracts ---")
    source_abi, source_bytecode = compile_solidity_file("Source.sol", "Source")
    dest_abi, dest_bytecode = compile_solidity_file("Destination.sol", "Destination")

    print("\n--- 2. Deploying Source Contract to Avalanche Fuji ---")
    source_address = deploy_contract(FUJI_RPC, private_key, source_abi, source_bytecode, "Avalanche Fuji")

    print("\n--- 3. Deploying Destination Contract to BNB Testnet ---")
    dest_address = deploy_contract(BSC_TESTNET_RPC, private_key, dest_abi, dest_bytecode, "BNB Testnet")

    print("\n--- 4. Updating contract_info.json ---")
    config["source"]["address"] = source_address
    config["source"]["abi"] = source_abi
    config["destination"]["address"] = dest_address
    config["destination"]["abi"] = dest_abi
    save_config(config)

if __name__ == "__main__":
    main()
