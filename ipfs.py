import json
import requests

INFURA_API = "https://ipfs.infura.io:5001"


def pin_to_ipfs(data):
    """Takes a Python dictionary, serializes it to JSON, and pins it to IPFS via Infura.

    Returns the Content Identifier (CID).
    """
    assert isinstance(data, dict), "Error: pin_to_ipfs expects a dictionary"

    # Convert dictionary to compact JSON bytes to ensure clean transmission
    json_bytes = json.dumps(data, separators=(",", ":")).encode("utf-8")

    # Structure the payload as a file multipart upload
    files = {"file": ("data.json", json_bytes, "application/json")}

    # Send POST request to the IPFS add endpoint
    response = requests.post(f"{INFURA_API}/api/v0/add", files=files)
    response.raise_for_status()

    # Parse response and extract the CID (Hash)
    result = response.json()
    cid = result["Hash"]

    return cid


def get_from_ipfs(cid, content_type="json"):
    """Takes an IPFS CID, fetches the data using Infura's POST 'cat' endpoint,

    and returns the content decoded as a Python dictionary.
    """
    assert isinstance(cid, str), "Error: get_from_ipfs accepts a cid as a string"

    # Infura expects the CID passed as the 'arg' URL parameter
    params = {"arg": cid}

    # As per instructions, using POST on the /cat endpoint due to /get limitations
    response = requests.post(f"{INFURA_API}/api/v0/cat", params=params)
    response.raise_for_status()

    # Parse JSON string back into a Python dictionary
    data = json.loads(response.text)

    assert isinstance(data, dict), "Error: get_from_ipfs should return a dict"

    return data