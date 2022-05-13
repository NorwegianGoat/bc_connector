from curses.ascii import HT
from email.policy import HTTP
from typing import List
from xmlrpc.server import SimpleXMLRPCServer
from utils.cb_wrapper import CBWrapper
from utils.resource_manager import available_contracts
from utils.contracts_utils import proof_maker, verify_bytecode, trie_maker, TRIES_BASEPATH, load_abi
from web3 import Web3, HTTPProvider
import logging
import os
import json
from merkletools import MerkleTools

SECRET_KEY_PATH = "resources/.secret"
CONTRACT_ABIS = "crosscoin/build/contracts"
# This is the address of the local root board (the contract in which the root state is committed)
LOCAL_BOARD = "0x054108eE0dc15Ef50b632734eE01174E2cfb9BbF"


class RelayerManager():
    def __init__(self, address: str, port: int, dst_endpoint: str):
        # Blockchain nodes and contracts
        self.src_endpoint = None
        self.dst_endpoint = Web3(HTTPProvider(dst_endpoint))
        self.src_addrs = None
        self.dst_addrs = None
        # XML-RPC config
        self.address = address
        self.port = port
        self.server = SimpleXMLRPCServer((self.address, self.port))
        self.relayer = CBWrapper()
        self.server.register_function(self.remap_relayer, "remap_relayer")
        self.server.serve_forever()

    def _get_addrs(self, src_bridge_addr, res_id):
        # src addrs
        bridge_abi = load_abi(os.path.join(CONTRACT_ABIS, "Bridge.json"))
        bridge = self.src_endpoint.eth.contract(
            abi=bridge_abi, address=src_bridge_addr)
        token_handler_addr = bridge.functions._resourceIDToHandlerAddress(
            res_id).call()
        token_handler_abi = load_abi(os.path.join(
            CONTRACT_ABIS, "ERC20Handler.json"))
        token_handler = self.src_endpoint.eth.contract(
            abi=token_handler_abi, address=token_handler_addr)
        token_addr = token_handler.functions._resourceIDToTokenContractAddress(
            res_id).call()
        self.src_addrs = [src_bridge_addr, token_handler_addr, token_addr]
        # dst addrs
        contracts = available_contracts(self.dst_endpoint.eth.chain_id, None)
        self.dst_addrs = []
        self.dst_addrs.append(contracts["bridge"].address)
        self.dst_addrs.append(contracts["handler"].address)
        self.dst_addrs.append(contracts["target"].address)
        logging.info("Found these addresses for source: " +
                     str(self.src_addrs))
        logging.info(
            "Found these addresses for destination: " + str(self.dst_addrs))

    def _bytecode_matches(self):
        # return verify_bytecode([self.src_endpoint.provider.endpoint_uri, self.dst_endpoint.provider.endpoint_uri], self.src_addrs, self.dst_addrs)
        return True

    def _get_root(self):
        board_abi = load_abi(os.path.join(CONTRACT_ABIS, "RootBoard.json"))
        board = self.dst_endpoint.eth.contract(
            abi=board_abi, address=LOCAL_BOARD)
        return board.functions.getLatestRoot(
            self.src_endpoint.eth.chain_id).call()

    def _write_root(self, nonce: int, root: str):
        board_abi = load_abi(os.path.join(CONTRACT_ABIS, "RootBoard.json"))
        board = self.dst_endpoint.eth.contract(
            abi=board_abi, address=LOCAL_BOARD)
        board.functions.setLatestRoot(
            nonce, root).call()

    def _storage_integrity(self):
        trie_path = os.path.join(TRIES_BASEPATH, str(
            self.src_endpoint.eth.chain_id)+".json")
        # If the path exists we know this chain, else is the first time we see it
        if os.path.exists(trie_path):
            with open(trie_path) as f:
                saved_trie = json.load(fp=f)
            trie = MerkleTools()
            for deposit in saved_trie["deposits"]:
                trie.add_leaf(deposit["data"], True)
            trie.make_tree()
            if trie.get_merkle_root() == self._get_root():
                logging.info("Our root does not match with the one saved on chain. " +
                             trie.get_merkle_root + " vs. " + self._get_root())
            else:
                return False
            # Read the storage on source chain and generate a proof for the last
            # deposit then check the proof against our saved trie
            latest_nonce_saved = int(saved_trie["deposits"][-1]['nonce'])
            user_trie = trie_maker(
                self.src_endpoint, self.dst_endpoint, self.src_addrs[0], latest_nonce_saved)
            proof = proof_maker(user_trie, latest_nonce_saved)
            if not trie.validate_proof(proof[0], proof[1], trie.get_merkle_root()):
                return False
        else:
            # TODO: Write new endpoints in db
            pass
        # Write the updated root on chain
        trie = trie_maker(
            self.src_endpoint, self.dst_endpoint, self.src_addrs[0], save_on_disk=True)
        with open(trie_path) as f:
            saved_trie = json.load(fp=f)
        self._write_root(saved_trie["deposits"][-1]
                         ["nonce"], trie.get_merkle_root())
        return True

    def remap_relayer(self, src_endpoint: str, from_block: int, src_bridge_addr: str, res_id: str):
        self.src_endpoint = Web3(HTTPProvider(src_endpoint))
        logging.info("User asked for relayer remapping: %s, %i, %i" %
                     (src_endpoint, self.src_endpoint.eth.chain_id, from_block))
        self._get_addrs(src_bridge_addr, res_id)
        # Check conditions for relayer remapping
        if self._bytecode_matches() and self._storage_integrity():
            if self.relayer.is_relayer_running():
                self.relayer.stop_relay()
            self.relayer.start_relay(latest=from_block)
            return {"response": "OK",
                    "extra": "We are parsing your events."}
        else:
            return {"response": "NOK",
                    "extra": "Your contract bytecode is different or smart contract storage has different transactions."}


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    srv = RelayerManager("192.168.1.110", 23456, "http://192.168.1.110:8545")
