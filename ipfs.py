import json
import requests

INFURA_API = "https://ipfs.infura.io:5001"

# Replace these with your actual credentials from the Infura Dashboard
INFURA_PROJECT_ID = "YOUR_INFURA_PROJECT_ID"
INFURA_PROJECT_SECRET = "YOUR_INFURA_PROJECT_SECRET"
AUTH = (INFURA_PROJECT_ID, INFURA_PROJECT_SECRET)


def pin_to_ipfs(data):
    assert isinstance(data, dict), "Error pin_to_ipfs expects a dictionary"

    json_bytes = json.dumps(data, separators=(",", ":")).encode("utf-8")
    files = {"file": ("data.json", json_bytes, "application/json")}

    # Added the 'auth' parameter here
    response = requests.post(
        f"{INFURA_API}/api/v0/add", files=files, auth=AUTH
    )
    response.raise_for_status()

    result = response.json()
    return result["Hash"]


def get_from_ipfs(cid, content_type="json"):
    assert isinstance(cid, str), "get_from_ipfs accepts a cid in the form of a string"

    params = {"arg": cid}

    # Added the 'auth' parameter here
    response = requests.post(
        f"{INFURA_API}/api/v0/cat", params=params, auth=AUTH
    )
    response.raise_for_status()

    data = json.loads(response.text)
    assert isinstance(data, dict), "get_from_ipfs should return a dict"

    return data