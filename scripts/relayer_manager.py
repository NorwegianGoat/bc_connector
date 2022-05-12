from typing import List
from xmlrpc.server import SimpleXMLRPCServer
from utils.cb_wrapper import CBWrapper
from utils.resource_manager import available_contracts
from utils.contracts_utils import proof_maker, verify_bytecode, trie_maker, TRIES_BASEPATH
from web3 import Web3, HTTPProvider
import logging
import os
import json
from merkletools import MerkleTools


class RelayerManager():
    def __init__(self, address: str, port: int, dst_endpoint: str):
        self.address = address
        self.port = port
        self.src_endpoint = None
        self.dst_endpoint = Web3(HTTPProvider(dst_endpoint))
        self.server = SimpleXMLRPCServer((self.address, self.port))
        self.relayer = CBWrapper()
        self.server.register_function(self.remap_relayer, "remap_relayer")
        self.server.serve_forever()

    def _bytecode_matches(self, src_endpoint: str, src_addrs: List[str]):
        contracts = available_contracts(self.dst_endpoint.eth.chain_id, None)
        dst_addrs = []
        dst_addrs.append(contracts["bridge"].address)
        dst_addrs.append(contracts["handler"].address)
        dst_addrs.append(contracts["target"].address)
        # return verify_bytecode([src_endpoint, self.dst_endpoint.provider.endpoint_uri], src_addrs, dst_addrs)
        return True

    def _storage_integrity(self, src_endpoint: str, chain_id: int, src_addrs: str):
        trie_path = os.path.join(TRIES_BASEPATH, str(chain_id)+".json")
        # If the path exists we know this chain, else is the first time we see it
        if os.path.exists(trie_path):
            with open(trie_path) as f:
                saved_trie = json.load(fp=f)
            trie = MerkleTools()
            for deposit in saved_trie["deposits"]:
                trie.add_leaf(deposit["data"], True)
            trie.make_tree()
            # TODO: Compare our root with the one saved on our chain
            #trie.get_merkle_root()
            # Read the storage on source chain and generate a proof for the last
            # deposit then check the proof against our saved trie
            latest_nonce_saved = int(saved_trie["deposits"][-1]['nonce'])
            user_trie = trie_maker(
                src_endpoint, self.dst_endpoint.provider.endpoint_uri, src_addrs[0], latest_nonce_saved)
            proof = proof_maker(user_trie, latest_nonce_saved)
            if not trie.validate_proof(proof[0], proof[1], trie.get_merkle_root()):
                return False
        else:
            # TODO: Write new endpoints in db
            pass
        trie = trie_maker(
            src_endpoint, self.dst_endpoint.provider.endpoint_uri, src_addrs[0], save_on_disk=True)
        # TODO: Commit new root on chain
        return True

    def remap_relayer(self, src_endpoint: str, from_block: int, src_addrs: str):
        self.src_endpoint = Web3(HTTPProvider(src_endpoint))
        logging.info("User asked for relayer remapping: %s, %i, %i" %
                     (src_endpoint, self.src_endpoint.eth.chain_id, from_block))
        # Check conditions for relayer remapping
        if self._bytecode_matches(src_endpoint, src_addrs) and self._storage_integrity(src_endpoint, self.src_endpoint.eth.chain_id, src_addrs):
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
