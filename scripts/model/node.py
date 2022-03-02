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


if __name__ == "__main__":
    # TODO: remove, it's just for debug
    n = Node("http://192.168.1.110:8545")
    tx = n.provider.eth.get_transaction_receipt(
        '0x4bc001f833c04635133461d97373418b3da0db0a0ae081a05c36aa61ae2d22f5')
    print(tx)
