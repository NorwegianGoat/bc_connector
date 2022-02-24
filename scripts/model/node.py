from web3 import Web3, HTTPProvider
import logging


class Node():
    # Default endpoint and chain id
    __NODE_ENDPOINT = "http://127.0.0.1:8545"
    __CHAIN_ID = 100

    def __init__(self, node_endpoint: str = __NODE_ENDPOINT, chain_id: int = __CHAIN_ID):
        self.node_endpoint = node_endpoint
        self.chain_id = chain_id
        self.provider = Web3(HTTPProvider(node_endpoint))
        if self.provider.isConnected():
            logging.info(node_endpoint + " is reachable.")
        else:
            logging.info("Attention! " + node_endpoint +
                         " seems to be unreachable.")

    def get_endpoint(self) -> str:
        return self.node_endpoint

    def get_chain_id(self) -> int:
        return self.chain_id

    def __str__(self) -> str:
        return "Endpoint: " + self.node_endpoint + " Chain Id: " + self.chain_id

if __name__=="__main__":
    n = Node("http://192.168.1.110:8545",100)
    print(n.provider.eth.chain_id)
