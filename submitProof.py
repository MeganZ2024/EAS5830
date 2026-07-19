import eth_account
import random
import string
import json
from pathlib import Path
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware  # Necessary for POA chains


def merkle_assignment():
    """
        The only modifications you need to make to this method are to assign
        your "random_leaf_index" and uncomment the last line when you are
        ready to attempt to claim a prime. You will need to complete the
        methods called by this method to generate the proof.
    """
    # Generate the list of primes as integers
    num_of_primes = 8192
    primes = generate_primes(num_of_primes)

    # Create a version of the list of primes in bytes32 format
    leaves = convert_leaves(primes)

    # Build a Merkle tree using the bytes32 leaves as the Merkle tree's leaves
    tree = build_merkle(leaves)

    # Select a random leaf and create a proof for that leaf
    # We use a random index from 1 to 8191 since index 0 (prime 2) is already claimed.
    random_leaf_index = random.randint(1, num_of_primes - 1) 
    proof = prove_merkle(tree, random_leaf_index)

    # This is the same way the grader generates a challenge for sign_challenge()
    challenge = ''.join(random.choice(string.ascii_letters) for i in range(32))
    # Sign the challenge to prove to the grader you hold the account
    addr, sig = sign_challenge(challenge)

    if sign_challenge_verify(challenge, addr, sig):
        tx_hash = '0x'
        # Complete this method and run your code with the following line un-commented
        tx_hash = send_signed_msg(proof, leaves[random_leaf_index])
        print(f"Transaction submitted! Hash: {tx_hash}")


def generate_primes(num_primes):
    """
        Function to generate the first 'num_primes' prime numbers
        returns list (with length n) of primes (as ints) in ascending order
    """
    primes_list = []
    candidate = 2
    while len(primes_list) < num_primes:
        for p in primes_list:
            if p * p > candidate:
                primes_list.append(candidate)
                break
            if candidate % p == 0:
                break
        else:
            if candidate not in primes_list:
                primes_list.append(candidate)
        candidate += 1
    return primes_list


def convert_leaves(primes_list):
    """
        Converts the leaves (primes_list) to bytes32 format
        returns list of primes where list entries are bytes32 encodings of primes_list entries
    """
    return [int.to_bytes(p, 32, 'big') for p in primes_list]


def build_merkle(leaves):
    """
        Function to build a Merkle Tree from the list of prime numbers in bytes32 format
        Returns the Merkle tree (tree) as a list where tree[0] is the list of leaves,
        tree[1] is the parent hashes, and so on until tree[n] which is the root hash
        the root hash produced by the "hash_pair" helper function
    """
    tree = [leaves]
    current_level = leaves
    
    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            # If there's an odd number of elements, pair the last element with itself
            if i + 1 < len(current_level):
                parent_hash = hash_pair(current_level[i], current_level[i+1])
            else:
                parent_hash = hash_pair(current_level[i], current_level[i])
            next_level.append(parent_hash)
        tree.append(next_level)
        current_level = next_level

    return tree


def prove_merkle(merkle_tree, random_indx):
    """
        Takes a random_index to create a proof of inclusion for and a complete Merkle tree
        as a list of lists where index 0 is the list of leaves, index 1 is the list of
        parent hash values, up to index -1 which is the list of the root hash.
        returns a proof of inclusion as list of values (hex strings or bytes)
    """
    merkle_proof = []
    idx = random_indx
    
    # Iterate through all levels except the root level
    for level in merkle_tree[:-1]:
        # Determine if the index is even or odd to find its sibling
        if idx % 2 == 0:
            # Sibling is to the right
            if idx + 1 < len(level):
                sibling = level[idx + 1]
            else:
                sibling = level[idx]  # Pair with itself if no right sibling exists
        else:
            # Sibling is to the left
            sibling = level[idx - 1]
            
        merkle_proof.append(sibling)
        idx //= 2  # Move to the parent index for the next level
        
    return merkle_proof


def sign_challenge(challenge):
    """
        Takes a challenge (string)
        Returns address, sig
        where address is an ethereum address and sig is a signature (in hex)
        This method is to allow the auto-grader to verify that you have
        claimed a prime
    """
    acct = get_account()
    addr = acct.address

    # Encode the message using the EIP-191 standard (Defunct prefix matches eth_sign format)
    eth_encoded_msg = eth_account.messages.encode_defunct(text=challenge)
    eth_sig_obj = acct.sign_message(eth_encoded_msg)

    return addr, eth_sig_obj.signature.hex()


def send_signed_msg(proof, random_leaf):
    """
        Takes a Merkle proof of a leaf, and that leaf (in bytes32 format)
        builds signs and sends a transaction claiming that leaf (prime)
        on the contract
    """
    chain = 'bsc'

    acct = get_account()
    contract_address, abi = get_contract_info(chain)
    w3 = connect_to(chain)

    contract = w3.eth.contract(address=contract_address, abi=abi)
    
    # Convert proof items into hex format strings if required by web3.py contract wrappers
    formatted_proof = [p.hex() if isinstance(p, bytes) else p for p in proof]
    formatted_leaf = random_leaf.hex() if isinstance(random_leaf, bytes) else random_leaf

    # Build the transaction using the contract's "submit" method
    # Note: Check your specific contract ABI if the function is lowercase 'submit'
    tx = contract.functions.submit(formatted_proof, formatted_leaf).build_transaction({
        'from': acct.address,
        'nonce': w3.eth.get_transaction_count(acct.address),
        'gasPrice': w3.eth.gas_price,
        'chainId': w3.eth.chain_id
    })
    
    # Estimate gas to prevent out-of-gas errors
    tx['gas'] = int(w3.eth.estimate_gas(tx) * 1.2)

    # Sign and broadcast the transaction
    signed_tx = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

    return tx_hash.hex()


# Helper functions that do not need to be modified
def connect_to(chain):
    if chain not in ['avax','bsc']:
        print(f"{chain} is not a valid option for 'connect_to()'")
        return None
    if chain == 'avax':
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc"
    else:
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/"
    w3 = Web3(Web3.HTTPProvider(api_url))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


def get_account():
    cur_dir = Path(__file__).parent.absolute()
    with open(cur_dir.joinpath('sk.txt'), 'r') as f:
        sk = f.readline().rstrip()
    if sk[0:2] == "0x":
        sk = sk[2:]
    return eth_account.Account.from_key(sk)


def get_contract_info(chain):
    contract_file = Path(__file__).parent.absolute() / "contract_info.json"
    if not contract_file.is_file():
        contract_file = Path(__file__).parent.parent.parent / "tests" / "contract_info.json"
    with open(contract_file, "r") as f:
        d = json.load(f)
        d = d[chain]
    return d['address'], d['abi']


def sign_challenge_verify(challenge, addr, sig):
    eth_encoded_msg = eth_account.messages.encode_defunct(text=challenge)
    if eth_account.Account.recover_message(eth_encoded_msg, signature=sig) == addr:
        print(f"Success: signed the challenge {challenge} using address {addr}!")
        return True
    else:
        print(f"Failure: The signature does not verify!")
        print(f"signature = {sig}\naddress = {addr}\nchallenge = {challenge}")
        return False


def hash_pair(a, b):
    if a < b:
        return Web3.solidity_keccak(['bytes32', 'bytes32'], [a, b])
    else:
        return Web3.solidity_keccak(['bytes32', 'bytes32'], [b, a])


if __name__ == "__main__":
    merkle_assignment()