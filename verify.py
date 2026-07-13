import os
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from eth_account.messages import encode_defunct
import random

def sign_challenge( challenge ):
    w3 = Web3()

    # Your private key (Keep the 0x prefix intact)
    sk = "0x0b230bc657981618781e18fdea1bcfd998416cae18bf957630e7c78330a8979f"

    acct = w3.eth.account.from_key(sk)
    signed_message = w3.eth.account.sign_message( challenge, private_key = acct.key )

    return acct.address, signed_message.signature


def verify_sig():
    """
    This is essentially the code that the autograder will use to test signChallenge.
    """
    challenge_bytes = random.randbytes(32)
    challenge = encode_defunct(challenge_bytes)
    address, sig = sign_challenge( challenge )

    w3 = Web3()
    return w3.eth.account.recover_message( challenge , signature=sig ) == address


def mint_nft_on_chain():
    """
    Executes the active on-chain interaction to claim an NFT with an optimized low Token ID.
    """
    RPC_URL = "https://api.avax-test.network/ext/bc/C/rpc"
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    # Inject Geth PoA Middleware required by Avalanche Fuji Testnet
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    
    if not w3.is_connected():
        print("[-] RPC connection failed.")
        return False

    sk = "0x0b230bc657981618781e18fdea1bcfd998416cae18bf957630e7c78330a8979f"
    account = Account.from_key(sk)
    
    contract_address = "0x85ac2e065d4526FBeE6a2253389669a12318A412"
    abi = [
        {
            "inputs": [
                {"internalType": "address", "name": "_to", "type": "address"},
                {"internalType": "bytes32", "name": "nonce", "type": "bytes32"}
            ],
            "name": "claim",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "nonpayable",
            "type": "function"
        },
        {
            "inputs": [],
            "name": "maxId",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [{"internalType": "address", "name": "owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function"
        }
    ]
    
    contract = w3.eth.contract(address=contract_address, abi=abi)
    
    # Check if this wallet already owns an NFT from a previous run
    if contract.functions.balanceOf(account.address).call() > 0:
        print("[+] Wallet already owns an NFT. Skipping minting process.")
        return True

    # Locally brute force a random nonce to secure a small token ID (< 50)
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

    # Build and broadcast the mint transaction
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
        print("[-] Transaction reverted. The token ID may have been sniped. Try running again.")
        return False


if __name__ == '__main__':
    print("--- Step 1: Claiming/Minting NFT on Avalanche Fuji ---")
    mint_success = mint_nft_on_chain()
    
    print("\n--- Step 2: Running Signature Verification Challenge ---")
    if mint_success and verify_sig():
        print("You passed the challenge!")
    else:
        print("You failed the challenge!")