from typing import List
from web3 import HTTPProvider, Web3
from eth_account import Account
import requests
import json
import logging
import os
from merkletools import MerkleTools

CONTRACT_ADDRESS = "0xAd28ab39509672F4D621206710654bd875D5fEa2"
NODE_ENDPOINT = "http://192.168.1.110:8545"

TRIES_BASEPATH = "resources/contract_storage_tries"
METADATA_DELIMITER = "264697066735822"

def verify_bytecode(node_endpoints: List[str], src_addrs: List[str], dst_addrs: List[str]) -> bool:
    src_bytecode = []
    dst_bytecode = []
    for i in range(0, len(src_addrs)):
        data = json.dumps({"jsonrpc": "2.0", "method": "eth_getCode",
                           "params": [src_addrs[i], "latest"], "id": 1})
        bytecode = json.loads(requests.post(
            url=node_endpoints[0], data=data).text)['result']
        bytecode = bytecode[bytecode.index(METADATA_DELIMITER):]
        src_bytecode.append(bytecode)
        data = json.dumps({"jsonrpc": "2.0", "method": "eth_getCode",
                           "params": [dst_addrs[i], "latest"], "id": 1})
        bytecode = json.loads(requests.post(
            url=node_endpoints[1], data=data).text)['result']
        bytecode = bytecode[bytecode.index(METADATA_DELIMITER):]
        dst_bytecode.append(bytecode)
    if src_bytecode == dst_bytecode:
        logging.info("Bytecode matches")
        return True
    else:
        logging.info("WARNING: Bytecode does not match!")
        return False


def load_abi(abi_path: str):
    with open(abi_path) as f:
        abi = json.load(f)
    return abi['abi']


def trie_maker(source_endpoint: Web3, dest_endpoint: Web3, src_bridge_addr: str, latest_nonce: int = None, save_on_disk: bool = False):
    abi = load_abi("crosscoin/build/contracts/BridgeWithdrawPatch.json")
    contract = source_endpoint.eth.contract(abi=abi, address=src_bridge_addr)
    if not latest_nonce:
        # Get the latest nonce used by source chain to dest chain
        latest_nonce = contract.functions._depositCounts(
            dest_endpoint.eth.chain_id).call()
    trie = MerkleTools()
    deposits = []
    # Get gets all the deposits records for this chainId up to the latest transfer
    for i in range(0, latest_nonce+1):
        deposit_data = contract.functions._depositRecords(
            i, dest_endpoint.eth.chain_id).call().hex()
        deposits.append({"nonce": i, "data": deposit_data})
        trie.add_leaf(deposit_data, True)
    # It creates the tree
    trie.make_tree()
    if save_on_disk:
        with open(os.path.join(TRIES_BASEPATH, str(source_endpoint.eth.chain_id)+".json"), mode="w") as f:
            json.dump({"deposits": deposits}, fp=f)
    return trie


def proof_maker(trie: MerkleTools, proof_index: int):
    path = trie.get_proof(proof_index)
    return path, trie.get_leaf(proof_index), trie.get_merkle_root()


def sign_message(account: Account, message: str):
    signed_message = account.sign_message()
    logging.info(signed_message)
