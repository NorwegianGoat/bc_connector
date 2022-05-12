from http import server
from typing import List
from xmlrpc.server import SimpleXMLRPCServer
from utils.cb_wrapper import CBWrapper
from utils.resource_manager import available_contracts
from utils.contracts_utils import verify_bytecode, proof_validator, trie_maker, TRIES_BASEPATH
from web3 import Web3, HTTPProvider
import logging
import os
import json


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
                trie = json.dumps(f.readlines())
                # TODO: check the last item
            if not proof_validator():
                return False
        else:
            # We create the new trie
            trie_maker(
                src_endpoint, self.dst_endpoint.provider.endpoint_uri, src_addrs[0])
            # TODO: Write new endpoints in db
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
