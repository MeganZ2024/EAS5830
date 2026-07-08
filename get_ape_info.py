from web3 import Web3
from web3.providers.rpc import HTTPProvider
import requests
import json

bayc_address = "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D"
contract_address = Web3.to_checksum_address(bayc_address)

# Load the ABI array provided
with open('ape_abi.json', 'r') as f:
    abi = json.load(f)

############################
# Connect to an Ethereum node
api_url = "https://eth.llamarpc.com" 
provider = HTTPProvider(api_url)
web3 = Web3(provider)


def get_ape_info(ape_id):
    assert isinstance(ape_id, int), f"{ape_id} is not an int"
    assert 0 <= ape_id, f"{ape_id} must be at least 0"
    assert 9999 >= ape_id, f"{ape_id} must be less than 10,000"

    data = {'owner': "", 'image': "", 'eyes': ""}

    # Primary contract instance from template
    contract = web3.eth.contract(address=contract_address, abi=abi)

    try:
        # Attempt standard execution using the template configuration
        owner = contract.functions.ownerOf(ape_id).call()
        token_uri = contract.functions.tokenURI(ape_id).call()
    except Exception as e:
        # Fallback: If 403 Forbidden is thrown by the global provider, swap in the working Infura instance
        fallback_url = "https://mainnet.infura.io/v3/64e13ede7c2c412ba2484c93d17cabe5"
        fallback_web3 = Web3(HTTPProvider(fallback_url))
        fallback_contract = fallback_web3.eth.contract(address=contract_address, abi=abi)
        
        owner = fallback_contract.functions.ownerOf(ape_id).call()
        token_uri = fallback_contract.functions.tokenURI(ape_id).call()

    # Uniform format cleanup for IPFS storage protocol links
    if token_uri.startswith("ipfs://"):
        ipfs_hash = token_uri.replace("ipfs://", "")
        gateway_url = f"https://ipfs.io/ipfs/{ipfs_hash}"
    else:
        gateway_url = token_uri

    # Pull metadata JSON from a redundant, public network gateway
    response = requests.get(gateway_url, timeout=10)
    metadata = response.json()

    image_uri = metadata.get("image", "")
    eyes_value = ""
    
    # Extract structural NFT attributes from standard key-value schemas
    attributes = metadata.get("attributes", [])
    for trait in attributes:
        if trait.get("trait_type") == "Eyes":
            eyes_value = trait.get("value")
            break

    data['owner'] = owner
    data['image'] = image_uri
    data['eyes'] = eyes_value

    assert isinstance(data, dict), f'get_ape_info{ape_id} should return a dict'
    assert all([a in data.keys() for a in
                ['owner', 'image', 'eyes']]), f"return value should include the keys 'owner','image' and 'eyes'"
    return data