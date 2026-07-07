from web3 import Web3
from web3.providers.rpc import HTTPProvider


def connect_to_eth():
    """
    Connect to Ethereum Mainnet.

    This implementation prioritizes stability in restricted environments
    such as Codio. Public endpoints are preferred; Infura is used as a
    secondary option.

    Returns:
        Web3: A connected Web3 instance.

    Raises:
        AssertionError: If no Ethereum node can be reached.
    """

    # Primary: Cloudflare public endpoint (very stable in Codio)
    cloudflare_url = "https://cloudflare-eth.com"

    # Fallback: Infura (requires API key)
    infura_url = (
        "https://mainnet.infura.io/v3/64e13ede7c2c412ba2484c93d17cabe5"
    )

    # Try Cloudflare first
    w3 = Web3(
        HTTPProvider(
            cloudflare_url,
            request_kwargs={
                "headers": {"User-Agent": "Mozilla/5.0"},
                "timeout": 30,
            },
        )
    )

    if w3.is_connected():
        # Sanity check: must be able to fetch a block
        latest_block = w3.eth.get_block("latest")
        assert latest_block is not None, "Failed to retrieve latest block"
        return w3

    # Fallback: Infura
    w3 = Web3(
        HTTPProvider(
            infura_url,
            request_kwargs={
                "headers": {"User-Agent": "Mozilla/5.0"},
                "timeout": 30,
            },
        )
    )

    if w3.is_connected():
        latest_block = w3.eth.get_block("latest")
        assert latest_block is not None, "Failed to retrieve latest block via Infura"
        return w3

    raise AssertionError(
        "Unable to connect to any Ethereum node "
        "(tried Cloudflare and Infura)"
    )