import requests
import json
import logging

CONTRACT_ABI = "https://ipfs.io/ipfs/QmaktJXwR8r5JQaCZaZ5KFrF44g8e4TsppgUZmgYxrKNKL"
CONTRACT_ADDRESS = "0xAd28ab39509672F4D621206710654bd875D5fEa2"
NODE_ENDPOINT = "http://192.168.1.110:8545"

def verify_bytecode(node_endpoint:str, abi_location:str, contract_address:str) -> bool:
    data = json.dumps({"jsonrpc": "2.0", "method": "eth_getCode",
                    "params": [contract_address, "latest"], "id": 1})
    bytecode_supplied = json.loads(requests.get(abi_location).text)[
        'deployedBytecode']
    bytecode_chain = json.loads(requests.post(
        url=node_endpoint, data=data).text)['result']
    if bytecode_chain == bytecode_supplied:
        logging.info("Bytecode matches")
        return True
    else:
        logging.info("WARNING: Bytecode does not match!")
        return False

if __name__=="__main__":
    verify_bytecode(NODE_ENDPOINT, CONTRACT_ABI, CONTRACT_ADDRESS)
