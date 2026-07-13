import os
import json
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
import random

# --- Robust Middleware Fallback Layer for web3.py v6 vs v7+ ---
try:
    from web3.middleware import ExtraDataToPOAMiddleware as poa_middleware
except ImportError:
    from web3.middleware import geth_poa_middleware as poa_middleware

def sign_challenge( challenge ):
    w3 = Web3()

    # Your persistent private key string
    sk = "0x0b230bc657981618781e18fdea1bcfd998416cae18bf957630e7c78330a8979f"

    acct = w3.eth.account.from_key(sk)
    signed_message = w3.eth.account.sign_message( challenge, private_key = acct.key )

    return acct.address, signed_message.signature


def verify_sig():
    """
    This replicates the exact code the autograder executes to test sign_challenge.
    """
    challenge_bytes = random.randbytes(32)
    challenge = encode_defunct(challenge_bytes)
    address, sig = sign_challenge( challenge )

    w3 = Web3()
    return w3.eth.account.recover_message( challenge , signature=sig ) == address


def mint_nft_on_chain():
    """
    Executes active on-chain interaction to secure a tiny Token ID using the local nft.abi file.
    """
    RPC_URL = "https://api.avax-test.network/ext/bc/C/rpc"
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    # Inject the resolved PoA Middleware layer securely into position 0
    w3.middleware_onion.inject(poa_middleware, layer=0)
    
    if not w3.is_connected():
        print("[-] RPC connection failed.")
        return False

    sk = "0x0b230bc657981618781e18fdea1bcfd998416cae18bf957630e7c78330a8979f"
    account = Account.from_key(sk)
    
    contract_address = "0x85ac2e065d4526FBeE6a2253389669a12318A412"
    
    # Dynamic ABI loading matching your previous structure
    abi_filename = "nft.abi"
    if not os.path.exists(abi_filename):
        # Fallback check if it's placed in the same folder as the script
        abi_filename = os.path.join(os.path.dirname(__file__), "nft.abi")
        
    try:
        with open(abi_filename, "r") as f:
            abi = json.load(f)
    except FileNotFoundError:
        print(f"[-] Error: Could not find '{abi_filename}' in the workspace.")
        return False

    contract = w3.eth.contract(address=contract_address, abi=abi)
    
    # Check if wallet already holds an NFT
    if contract.functions.balanceOf(account.address).call() > 0:
        print("[+] Wallet already owns an NFT. Skipping minting process.")
        return True

    # Brute force optimized small ID mapping locally 
    print("[+] Hunting for an optimized tiny Token ID locally...")
    try:
        max_id = contract.functions.maxId().call()
    except Exception:
        max_id = 10000

    while True:
        nonce_bytes = os.urandom(32)
        hashed = Web3.solidity_keccak(['bytes32'], [nonce_bytes])
        predicted_id = int.from_bytes(hashed, byteorder='big') % max_id
        if predicted_id < 50:
            print(f"[+] Found optimized nonce. Target Token ID: {predicted_id}")
            break

    # Build and dispatch contract mint payload
    print("[+] Dispatching contract claim transaction...")
    tx = contract.functions.claim(account.address, nonce_bytes).build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gasPrice': w3.eth.gas_price,
        'chainId': 43113
    })
    
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=sk)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    print(f"[+] Broadcast successful. Tx Hash: {tx_hash.hex()}")
    
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status == 1:
        print(f"[+] NFT successfully minted in block {receipt.blockNumber}!")
        return True
    else:
        print("[-] Transaction reverted. Try running again.")
        return False


if __name__ == '__main__':
    print("--- Step 1: Claiming/Minting NFT on Avalanche Fuji ---")
    mint_success = mint_nft_on_chain()
    
    print("\n--- Step 2: Running Signature Verification Challenge ---")
    if mint_success and verify_sig():
        print("You passed the challenge!")
    else:
        print("You failed the challenge!")