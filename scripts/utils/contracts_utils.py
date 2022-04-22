from web3 import HTTPProvider, Web3
from eth_account import Account
import requests
import json
import logging
from trie import BinaryTrie

CONTRACT_ABI = "https://ipfs.io/ipfs/QmaktJXwR8r5JQaCZaZ5KFrF44g8e4TsppgUZmgYxrKNKL"
CONTRACT_ADDRESS = "0xAd28ab39509672F4D621206710654bd875D5fEa2"
NODE_ENDPOINT = "http://192.168.1.110:8545"

def verify_bytecode_remote_abi(node_endpoint:str, abi_location:str, contract_address:str) -> bool:
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


def load_abi(abi_path: str):
    with open(abi_path) as f:
        abi = json.load(f)
    return abi


def proof_maker(source_endpoint: str, dest_endpoint: str, src_bridge_addr: str, dest_bridge_addr: str):
    source = Web3(HTTPProvider(source_endpoint))
    dest = Web3(HTTPProvider(dest_endpoint))
    abi = load_abi("crosscoin/build/contracts/Bridge.json")['abi']
    contract = source.eth.contract(abi=abi, address=src_bridge_addr)
    # Get the latest nonce used by source chain to dest chain
    latest_nonce = contract.functions._depositCounts(dest.eth.chainId).call()
    trie = BinaryTrie({})
    for i in range(0, latest_nonce+1):
        deposit_data = contract.functions._depositRecords(i, dest.eth.chainId).call()
        trie.set(Web3.toBytes(i),deposit_data)
    print(trie.get(Web3.toBytes(i)))

def sign_message(account:Account, message:str):
    signed_message = account.sign_message()
    logging.info(signed_message)
    
if __name__ == "__main__":
    # verify_bytecode(NODE_ENDPOINT, CONTRACT_ABI, CONTRACT_ADDRESS)
    src_bridge_addr = "0xAd28ab39509672F4D621206710654bd875D5fEa2"
    dst_bridge_addr = "0x3ab2A28A2a95FA7bbBdF8DfED9e6D945E99dDf38"
    proof_maker("http://192.168.1.110:8545",
                "http://192.168.1.120:8545", src_bridge_addr, dst_bridge_addr)


