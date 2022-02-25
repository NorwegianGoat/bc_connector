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

    def get_endpoint(self) -> str:
        return self.node_endpoint

    def get_chain_id(self) -> int:
        return self.chain_id

    def __str__(self) -> str:
        return "Endpoint: " + self.node_endpoint + " Chain Id: " + self.chain_id


if __name__ == "__main__":
    n = Node("http://192.168.1.110:8545", 100)
    '''block = n.provider.eth.get_block(4088, True)
    for tx in block['transactions']:
        print(str(tx['nonce']) + " " + tx['hash'].hex() + " " + tx['from'] + " " + tx['to'])'''
    tx = n.provider.eth.get_transaction_receipt('0x4461ee0cef0e1cd52ed9adff58dcd7ffd56587e0ee64154f7c526747b0b93129')
    print("APPROVE")
    print(tx)
    print("TRANSFER")
    tx = n.provider.eth.get_transaction_receipt('0x2b867bcd25d2a893661648df590c14a684a9c4b280c2568dfa0629610464d7f3')
    print(tx)
