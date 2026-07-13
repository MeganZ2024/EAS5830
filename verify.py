import os
import json
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
import random

# --- Compatibility Layer for web3.py v6 vs v7+ ---
try:
    from web3.middleware import ExtraDataToPOAMiddleware as poa_middleware
except ImportError:
    from web3.middleware import geth_poa_middleware as poa_middleware

def sign_challenge( challenge ):
    w3 = Web3()

    # Your persistent course private key string
    sk = "0x0b230bc657981618781e18fdea1bcfd998416cae18bf957630e7c78330a8979f"

    acct = w3.eth.account.from_key(sk)

    # Clean execution: Direct signature to prevent double-wrapping errors
    signed_message = w3.eth.account.sign_message( challenge, private_key = acct.key )

    return acct.address, signed_message.signature


def verify_sig():
    """
    Simulates the exact verification flow executed by the autograder.
    """
    challenge_bytes = random.randbytes(32)
    challenge = encode_defunct(challenge_bytes)
    address, sig = sign_challenge( challenge )

    w3 = Web3()
    return w3.eth.account.recover_message( challenge , signature=sig ) == address


def mint_nft_on_chain():
    """
    Connects to Avalanche Fuji, brute-forces a nonce for Token ID 0 or 1, and mints it.
    """
    RPC_URL = "https://api.avax-test.network/ext/bc/C/rpc"
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    w3.middleware_onion.inject(poa_middleware, layer=0)
    
    if not w3.is_connected():
        print("[-] RPC connection failed.")
        return False

    sk = "0x0b230bc657981618781e18fdea1bcfd998416cae18bf957630e7c78330a8979f"
    account = Account.from_key(sk)
    contract_address = "0x85ac2e065d4526FBeE6a2253389669a12318A412"
    
    # Resolve the correct directory path for the ABI file
    base_dir = "/home/codio/workspace/.guides/student_code/EAS5830"
    abi_filename = os.path.join(base_dir, "nft.abi")
    if not os.path.exists(abi_filename):
        abi_filename = "nft.abi"

    try:
        with open(abi_filename, "r") as f:
            abi = json.load(f)
    except Exception as e:
        print(f"[-] Failed to load ABI file: {e}")
        return False

    contract = w3.eth.contract(address=contract_address, abi=abi)

    try:
        max_id = contract.functions.maxId().call()
    except Exception:
        max_id = 10000

    # Brute force the absolute minimum global Token ID (0 or 1) locally
    print("[+] Locally hunting for an optimized nonce targeting Token ID 0 or 1...")
    while True:
        nonce_bytes = os.urandom(32)
        hashed = Web3.solidity_keccak(['bytes32'], [nonce_bytes])
        predicted_id = int.from_bytes(hashed, byteorder='big') % max_id
        if predicted_id in [0, 1]:
            print(f"[+] Match found! Target Token ID: {predicted_id}")
            break

    print("[+] Constructing and sending on-chain claim transaction...")
    try:
        tx = contract.functions.claim(account.address, nonce_bytes).build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gasPrice': w3.eth.gas_price,
            'chainId': 43113
        })
        
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=sk)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"[+] Broadcast successful. Transaction Hash: {tx_hash.hex()}")
        
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if receipt.status == 1:
            print(f"[+] NFT successfully minted in block {receipt.blockNumber}!")
            return True
        else:
            print("[-] Transaction reverted. The Token ID might have been taken. Please retry.")
            return False
    except Exception as tx_error:
        print(f"[-] Transaction failed: {tx_error}")
        return False


if __name__ == '__main__':
    print("--- Step 1: Claiming/Minting NFT on Avalanche Fuji ---")
    mint_nft_on_chain()
    
    print("\n--- Step 2: Running Cryptographic Signature Challenge ---")
    if verify_sig():
        print("You passed the challenge!")
    else:
        print("You failed the challenge!")