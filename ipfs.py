import json
import requests

# 1. READ CONFIGURATION (Public Gateway - No Auth Required)
PUBLIC_GATEWAY = "https://cloudflare-ipfs.com/ipfs"
# Alternative: "https://ipfs.io/ipfs"

# 2. WRITE CONFIGURATION (Pinata Free Tier)
# Sign up at https://www.pinata.cloud/ to get your free JWT token
PINATA_JWT = "PASTE_YOUR_PINATA_JWT_TOKEN_HERE"


def pin_to_ipfs(data):
    assert isinstance(data, dict), "Error pin_to_ipfs expects a dictionary"

    # Pinata API endpoint for pinning JSON directly
    url = "https://api.pinata.cloud/pinning/pinJSONToIPFS"

    headers = {
        "Authorization": f"Bearer {PINATA_JWT}",
        "Content-Type": "application/json",
    }

    payload = {"pinataContent": data, "pinataMetadata": {"name": "data.json"}}

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()

    result = response.json()
    # Pinata returns the CID under the key "IpfsHash"
    return result["IpfsHash"]


def get_from_ipfs(cid, content_type="json"):
    assert isinstance(cid, str), "get_from_ipfs accepts a cid in the form of a string"

    # Clean up the CID to ensure it appends cleanly to the gateway URL
    cid = cid.strip("/")

    # Fetch directly from a wide-open public gateway using a standard GET request
    url = f"{PUBLIC_GATEWAY}/{cid}"

    response = requests.get(url)
    response.raise_for_status()

    data = response.json()
    assert isinstance(data, dict), "get_from_ipfs should return a dict"

    return data