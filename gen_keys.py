#!/usr/bin/env python3
import os
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct

def get_keys(challenge, filename="secret_key.txt"):
    """
    Reads the persistent private key, signs the incoming challenge, 
    verifies the signature locally, and returns the wallet address and hex signature.
    
    Parameters:
        challenge (str/bytes): The message payload to sign.
        filename (str): The storage path for the persistent private key.
        
    Returns:
        tuple: (eth_addr, signature_hex)
    """
    
    # 1. Initialize persistent private key if the file does not exist
    if not os.path.exists(filename) or os.path.getsize(filename) == 0:
        new_account = Account.create()
        with open(filename, "w") as f:
            f.write(new_account.key.hex())
        print(f"\n[!] New key generated and saved to {filename}")
        print(f"[!] Target Wallet Address: {new_account.address}")
        print("[!] CRITICAL: Copy this address and fund it via BSC & Avalanche faucets now!\n")

    # 2. Read the existing private key from the storage file
    with open(filename, "r") as f:
        lines = f.readlines()
    
    assert len(lines) > 0, f"Your account file {filename} is empty"
    private_key = lines[0].strip()

    # 3. Derive the public wallet address from the private key
    account = Account.from_key(private_key)
    eth_addr = account.address

    # 4. Wrap the challenge using EIP-191 standard via encode_defunct
    if isinstance(challenge, bytes):
        message = encode_defunct(primitive=challenge)
    else:
        message = encode_defunct(text=str(challenge))

    # 5. Cryptographically sign the message payload
    signed_message = Account.sign_message(message, private_key=private_key)
    signature_hex = signed_message.signature.hex()

    # 6. Safety check to verify the signature matches the local wallet address
    recovered_addr = Account.recover_message(message, signature=signature_hex)
    assert recovered_addr == eth_addr, "Failed to sign message properly"

    return eth_addr, signature_hex


def sign_message(challenge, filename="secret_key.txt"):
    """
    Autograder compatibility wrapper. Matches the exact signature requested by validate.py:
    sig, addr = sign_message(challenge=challenge, filename=sk_filepath)
    
    Returns:
        tuple: (signed_message_object, eth_addr) 
        where signed_message_object has the '.signature' attribute needed by validate.py.
    """
    # Read the existing private key securely
    with open(filename, "r") as f:
        private_key = f.readline().strip()
        
    account = Account.from_key(private_key)
    eth_addr = account.address

    # Encode the message properly
    if isinstance(challenge, bytes):
        message = encode_defunct(primitive=challenge)
    else:
        message = encode_defunct(text=str(challenge))
        
    # Generate the actual SignedMessage object instead of a string
    signed_message_object = Account.sign_message(message, private_key=private_key)
    
    # Return (Object, String) to perfectly match 'sig, addr' assignment unpacking
    return signed_message_object, eth_addr


if __name__ == "__main__":
    # Local verification block replicating the autograder framework execution
    print("Executing local sanity checks...")
    for i in range(3):
        test_challenge = os.urandom(64)
        addr, sig = get_keys(challenge=test_challenge)
        print(f"Run {i+1} -> Signed by: {addr}")