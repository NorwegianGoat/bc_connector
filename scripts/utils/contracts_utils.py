from web3 import HTTPProvider, Web3
from eth_account import Account
import requests
import json
import logging
import os
from merkletools import MerkleTools

CONTRACT_ABI = "https://ipfs.io/ipfs/QmaktJXwR8r5JQaCZaZ5KFrF44g8e4TsppgUZmgYxrKNKL"
CONTRACT_ADDRESS = "0xAd28ab39509672F4D621206710654bd875D5fEa2"
NODE_ENDPOINT = "http://192.168.1.110:8545"

TRIES_BASEPATH = "resources/contract_storage_tries"


def verify_bytecode_remote_abi(node_endpoint: str, abi_location: str, contract_address: str) -> bool:
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


def trie_maker(source_endpoint: str, dest_endpoint: str, src_bridge_addr: str):
    source = Web3(HTTPProvider(source_endpoint))
    dest = Web3(HTTPProvider(dest_endpoint))
    abi = load_abi("crosscoin/build/contracts/Bridge.json")['abi']
    contract = source.eth.contract(abi=abi, address=src_bridge_addr)
    # Get the latest nonce used by source chain to dest chain
    latest_nonce = contract.functions._depositCounts(dest.eth.chainId).call()
    trie = MerkleTools()
    dict = {}
    # Get gets all the deposits records for this chainId up to the latest transfer
    for i in range(0, latest_nonce+1):
        deposit_data = contract.functions._depositRecords(
            i, dest.eth.chainId).call().hex()
        dict[i] = deposit_data
        trie.add_leaf(deposit_data)
    # It creates the tree
    trie.make_tree()
    with open(os.path.join(TRIES_BASEPATH,str(source.eth.chain_id)+".json"), mode="w") as f:
        json.dump(dict, fp=f)
    return trie


def proof_maker(trie: MerkleTools, proof_index: int):
    path = trie.get_proof(proof_index)
    return path, trie.get_leaf(proof_index), trie.get_merkle_root()


def proof_validator(source_chain_id, path, target, root):
    # Restore latest trie
    dict = {}
    with open(os.path.join(TRIES_BASEPATH,str(source_chain_id)+".json"), mode="r") as f:
        dict = json.load(fp=f)
    for key, value in dict.items():
        trie = MerkleTools()
        trie.add_leaf(value)
    # Make the trie and get response
    trie.make_tree()
    return trie.validate_proof(path, target, root)


def sign_message(account: Account, message: str):
    signed_message = account.sign_message()
    logging.info(signed_message)


if __name__ == "__main__":
    # verify_bytecode(NODE_ENDPOINT, CONTRACT_ABI, CONTRACT_ADDRESS)
    src_bridge_addr = "0xAd28ab39509672F4D621206710654bd875D5fEa2"
    dst_bridge_addr = "0x3ab2A28A2a95FA7bbBdF8DfED9e6D945E99dDf38"
    trie = trie_maker("http://192.168.1.110:8545",
                      "http://192.168.1.120:8545", src_bridge_addr)
    path, target, root = proof_maker(trie, 79)
    print(proof_validator(100, path, target, root))
