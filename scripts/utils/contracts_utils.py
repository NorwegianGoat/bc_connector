from typing import List
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


def verify_bytecode(node_endpoints: List[str], src_addrs: List[str], dst_addrs: List[str]) -> bool:
    src_bytecode = []
    dst_bytecode = []
    for i in range(0, len(src_addrs)):
        data = json.dumps({"jsonrpc": "2.0", "method": "eth_getCode",
                           "params": [src_addrs[i], "latest"], "id": 1})
        src_bytecode.append(json.loads(requests.post(
            url=node_endpoints[0], data=data).text)['result'])
        data = json.dumps({"jsonrpc": "2.0", "method": "eth_getCode",
                           "params": [dst_addrs[i], "latest"], "id": 1})
        dst_bytecode.append(json.loads(requests.post(
            url=node_endpoints[1], data=data).text)['result'])
    if src_bytecode == dst_bytecode:
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
    with open(os.path.join(TRIES_BASEPATH, str(source.eth.chain_id)+".json"), mode="w") as f:
        json.dump(dict, fp=f)
    return trie


def proof_maker(trie: MerkleTools, proof_index: int):
    path = trie.get_proof(proof_index)
    return path, trie.get_leaf(proof_index), trie.get_merkle_root()


def proof_validator(source_chain_id, path, target, root):
    # Restore latest trie
    dict = {}
    with open(os.path.join(TRIES_BASEPATH, str(source_chain_id)+".json"), mode="r") as f:
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
