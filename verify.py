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

def sign_challenge(challenge):
    w3 = Web3()
    
    # Securely reference your generated course account private key
    sk = "0x0b230bc657981618781e18fdea1bcfd998416cae18bf957630e7c78330a8979f"
    
    acct = w3.eth.account.from_key(sk)
    
    # EIP-191 compliant message signing required by the autograder challenge
    if isinstance(challenge, bytes):
        message = encode_defunct(primitive=challenge)
    else:
        message = encode_defunct(text=str(challenge))
        
    signed_message = w3.eth.account.sign_message(message, private_key=acct.key)
    return acct.address, signed_message.signature


def verify_sig():
    """
    Simulates the exact verification sequence utilized by the autograder.
    """
    challenge_bytes = random.randbytes(32)
    challenge = encode_defunct(challenge_bytes)
    address, sig = sign_challenge(challenge_bytes)

    w3 = Web3()
    return w3.eth.account.recover_message(challenge, signature=sig) == address


def mint_mcit_token():
    """
    Interacts with the current MCIT Token Contract to ensure the address holds an asset.
    """
    RPC_URL = "https://api.avax-test.network/ext/bc/C/rpc"
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    w3.middleware_onion.inject(poa_middleware, layer=0)
    
    if not w3.is_connected():
        print("[-] RPC connection to Avalanche Fuji failed.")
        return False

    sk = "0x0b230bc657981618781e18fdea1bcfd998416cae18bf957630e7c78330a8979f"
    account = Account.from_key(sk)
    
    # Absolute path targeting the provided ABI descriptor
    base_dir = "/home/codio/workspace/.guides/student_code/EAS5830"
    abi_filename = os.path.join(base_dir, "nft.abi")
    if not os.path.exists(abi_filename):
        abi_filename = "nft.abi"

    try:
        with open(abi_filename, "r") as f:
            abi = json.load(f)
    except Exception as e:
        print(f"[-] Missing or unreadable ABI layout: {e}")
        return False

    # Target contract instance
    contract_address = "0x85ac2e065d4526FBeE6a2253389669a12318A412"
    contract = w3.eth.contract(address=contract_address, abi=abi)

    # Inspect current inventory status
    try:
        balance = contract.functions.balanceOf(account.address).call()
        print(f"[+] Current contract asset balance: {balance}")
        if balance > 0:
            print("[+] Wallet already satisfies ownership check criteria.")
            return True
    except Exception as e:
        print(f"[-] Failed to execute balance verification: {e}")

    # Inspect the ABI to find the correct write function name designated for minting
    # Common ERC-721 mint selectors: 'mint', 'mintNFT', 'requestToken', or 'claim'
    function_names = [f['name'] for f in abi if f.get('type') == 'function']
    print(f"[+] Found available contract functions: {function_names}")
    
    # Dynamically resolve structural parameters for the target call
    print("[+] Submitting transaction to on-chain contract...")
    try:
        # Defaults to 'claim' variant matching the provided contract metadata rules
        if 'claim' in function_names:
            # Generate valid pseudo-random bytes32 variable parameters matching the interface
            nonce_bytes = os.urandom(32)
            tx_builder = contract.functions.claim(account.address, nonce_bytes)
        elif 'mint' in function_names:
            tx_builder = contract.functions.mint(account.address)
        else:
            print("[-] Standard entry-point execution method unrecognized in ABI description.")
            return False

        tx = tx_builder.build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gasPrice': w3.eth.gas_price,
            'chainId': 43113
        })
        
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=sk)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"[+] Tx submitted to network. Hash: {tx_hash.hex()}")
        
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if receipt.status == 1:
            print(f"[+] Asset successfully minted in block: {receipt.blockNumber}")
            return True
        print("[-] Blockchain transaction reverted.")
        return False
    except Exception as tx_err:
        print(f"[-] Transmission error encountered: {tx_err}")
        return False


if __name__ == '__main__':
    print("--- Step 1: Processing Account Token Inventory Configuration ---")
    mint_nft_on_chain = mint_mcit_token()
    
    print("\n--- Step 2: Running Challenge Authentication Pass ---")
    if verify_sig():
        print("You passed the local cryptographic challenge!")
    else:
        print("You failed the cryptographic challenge!")