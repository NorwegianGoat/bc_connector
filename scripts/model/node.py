from web3 import Web3, HTTPProvider
import logging
from web3.middleware.geth_poa import geth_poa_middleware


class Node():
    # Default endpoint and chain id
    __NODE_ENDPOINT = "http://127.0.0.1:8545"

    def __init__(self, node_endpoint: str = __NODE_ENDPOINT):
        self.node_endpoint = node_endpoint
        self.provider = Web3(HTTPProvider(node_endpoint))
        self.chain_id = self.provider.eth.chain_id
        self.provider.middleware_onion.inject(geth_poa_middleware, layer=0)
        if self.provider.isConnected():
            logging.info(node_endpoint + " is reachable.")
        else:
            logging.info("Attention! " + node_endpoint +
                         " seems to be unreachable.")

    def __str__(self) -> str:
        return "Endpoint: " + self.node_endpoint + " Chain Id: " + self.chain_id
