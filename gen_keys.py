import os
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct

def get_keys(challenge, filename="secret_key.txt"):
    """
     challenge - Can be a string or byte string (handled flexibly via encode_defunct)
     filename  - The filename containing your persistent 64-byte/character private key
    
    This function reads your saved key, signs the incoming challenge, 
    verifies it locally, and returns (address, signature_hex) to pass the autograder.
    """
    
    # 1. Check if the file exists and is not empty. 
    # If it doesn't exist, we generate a fresh persistent key so you don't crash.
    if not os.path.exists(filename) or os.path.getsize(filename) == 0:
        new_account = Account.create()
        with open(filename, "w") as f:
            f.write(new_account.key.hex())
        print(f"\n[!] New key generated and saved to {filename}")
        print(f"[!] Target Wallet Address: {new_account.address}")
        print("[!] CRITICAL: Copy this address and fund it via BSC & Avalanche faucets now!\n")

    # 2. Read the private key from the plaintext file
    with open(filename, "r") as f:
        lines = f.readlines()
    
    assert len(lines) > 0, f"Your account {filename} is empty"
    private_key = lines[0].strip()

    # 3. Derive the account address from the private key
    account = Account.from_key(private_key)
    eth_addr = account.address

    # 4. Wrap the challenge using EIP-191 standard via encode_defunct
    # Works seamlessly whether challenge is passed as 'text=...' or 'primitive=...'
    if isinstance(challenge, bytes):
        message = encode_defunct(primitive=challenge)
    else:
        message = encode_defunct(text=str(challenge))

    # 5. Sign the message using the private key
    signed_message = Account.sign_message(message, private_key=private_key)
    signature_hex = signed_message.signature.hex()

    # 6. Safety check matching the assignment signature verification rule
    recovered_addr = Account.recover_message(message, signature=signature_hex)
    assert recovered_addr == eth_addr, "Failed to sign message properly"

    # Return the exact two components required by the autograder
    return eth_addr, signature_hex


if __name__ == "__main__":
    # Local mock testing loop replicating the autograder's behavior
    print("Executing local sanity checks...")
    for i in range(3):
        # Testing with a random 64-byte challenge string
        test_challenge = os.urandom(64)
        addr, sig = get_keys(challenge=test_challenge)
        print(f"Run {i+1} -> Signed by: {addr}")