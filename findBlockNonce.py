import hashlib
import random
import string

def mine_block(k, prev_hash, rand_lines):
    """
    Finds a valid nonce such that SHA256(prev_hash + rand_lines + nonce)
    has at least k trailing zeros (Least Significant Bits) in its binary form.
    
    Parameters:
    k (int): Difficulty level (number of trailing bits that must be 0)
    prev_hash (bytes): The hash of the previous block
    rand_lines (list of str): The transactions/lines included in this block
    
    Returns:
    bytes: The valid nonce encoded in bytes
    """
    # 1. Initialize the base hash state with the invariant parts of the block
    base_hash = hashlib.sha256()
    base_hash.update(prev_hash)
    
    for line in rand_lines:
        base_hash.update(line.encode('utf-8'))
        
    # 2. Create a bitmask to easily check the k Least Significant Bits (LSB)
    # E.g., if k=3, mask is (1 << 3) - 1 = 7 (binary: 000...0111)
    mask = (1 << k) - 1
    
    nonce_counter = 0
    
    # 3. Brute-force loop to find the valid nonce
    while True:
        # Generate the nonce as a string and encode it to bytes
        nonce_str = str(nonce_counter)
        nonce_bytes = nonce_str.encode('utf-8')
        
        # Clone the base hash state and add the current nonce bytes
        current_hash = base_hash.copy()
        current_hash.update(nonce_bytes)
        
        # Get the hex string and convert the first 8 bytes of it into an integer
        # (Using the last few characters of the hex string to evaluate trailing bits)
        hex_digest = current_hash.hexdigest()
        
        # Take the last 16 hex characters (64 bits) which is plenty to evaluate k up to 10+
        last_64_bits = int(hex_digest[-16:], 16)
        
        # Check if the k LSBs are all zeros
        if (last_64_bits & mask) == 0:
            return nonce_bytes
            
        nonce_counter += 1

# --- Local Testing Framework ---
def get_random_lines():
    """Simulates random whitepaper text lines for testing."""
    sample_pool = [
        "Bitcoin: A Peer-to-Peer Electronic Cash System",
        "Ethereum: A Next-Generation Smart Contract and Decentralized Application Platform",
        "The root problem with conventional currency is all the trust that's required to make it work.",
        "A purely peer-to-peer version of electronic cash would allow online payments to be sent directly."
    ]
    return [random.choice(sample_pool) for _ in range(3)]

if __name__ == "__main__":
    print("--- Starting Mining Test ---")
    
    # Create mock inputs for verification
    mock_prev_hash = hashlib.sha256(b"genesis_block").digest()
    mock_txs = get_random_lines()
    difficulty = 10  # Codio will test up to around k=10
    
    print(f"Mining with Difficulty (k) = {difficulty}...")
    print(f"Transactions: {mock_txs}")
    
    # Run the miner
    found_nonce = mine_block(difficulty, mock_prev_hash, mock_txs)
    
    # Verify final result properties
    final_hash = hashlib.sha256()
    final_hash.update(mock_prev_hash)
    for tx in mock_txs:
        final_hash.update(tx.encode('utf-8'))
    final_hash.update(found_nonce)
    
    hex_res = final_hash.hexdigest()
    bin_res = bin(int(hex_res, 16))[2:].zfill(256)
    
    print("\n--- Mining Success! ---")
    print(f"Found Nonce (bytes): {found_nonce}")
    print(f"Resulting Hex Hash : {hex_res}")
    print(f"Trailing Bits Look : ...{bin_res[-20:]} (Should end with at least {difficulty} zeros)")