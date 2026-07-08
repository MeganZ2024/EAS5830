from web3 import Web3
from web3.providers.rpc import HTTPProvider
import requests
import json

bayc_address = "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D"
contract_address = Web3.to_checksum_address(bayc_address)

# You will need the ABI to connect to the contract
# The file 'ape_abi.json' has the ABI for the bored ape contract
with open('ape_abi.json', 'r') as f:
    abi = json.load(f)

############################
# Connect to an Ethereum node
# NOTE: Replace this URL with your actual Infura, Alchemy, or public RPC endpoint.
api_url = "https://eth.llamarpc.com" 
provider = HTTPProvider(api_url)
web3 = Web3(provider)


def get_ape_info(ape_id):
    assert isinstance(ape_id, int), f"{ape_id} is not an int"
    assert 0 <= ape_id, f"{ape_id} must be at least 0"
    assert 9999 >= ape_id, f"{ape_id} must be less than 10,000"

    data = {'owner': "", 'image': "", 'eyes': ""}

    # 1. Instantiate the contract using web3
    contract = web3.eth.contract(address=contract_address, abi=abi)

    # 2. Fetch the owner address and the tokenURI from the blockchain
    # 'ownerOf' and 'tokenURI' are standard ERC-721 functions
    owner = contract.functions.ownerOf(ape_id).call()
    token_uri = contract.functions.tokenURI(ape_id).call()

    # 3. Format the IPFS URI to use a public gateway for the HTTP request
    # Convert 'ipfs://Qm...' to 'https://ipfs.io/ipfs/Qm...'
    if token_uri.startswith("ipfs://"):
        ipfs_hash = token_uri.replace("ipfs://", "")
        gateway_url = f"https://ipfs.io/ipfs/{ipfs_hash}"
    else:
        gateway_url = token_uri

    # 4. Fetch the metadata JSON from IPFS
    response = requests.get(gateway_url)
    metadata = response.json()

    # 5. Extract 'image' and find the 'eyes' attribute from the metadata list
    image_uri = metadata.get("image", "")
    
    eyes_value = ""
    # Attributes are typically stored as a list of dicts: [{'trait_type': 'Eyes', 'value': 'Blue Beams'}]
    attributes = metadata.get("attributes", [])
    for trait in attributes:
        if trait.get("trait_type") == "Eyes":
            eyes_value = trait.get("value")
            break

    # Populating our return dictionary
    data['owner'] = owner
    data['image'] = image_uri
    data['eyes'] = eyes_value

    assert isinstance(data, dict), f'get_ape_info{ape_id} should return a dict'
    assert all([a in data.keys() for a in
                ['owner', 'image', 'eyes']]), f"return value should include the keys 'owner','image' and 'eyes'"
    return data