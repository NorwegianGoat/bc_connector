from http import server
from typing import List
from xmlrpc.server import SimpleXMLRPCServer
from utils.cb_wrapper import CBWrapper
from utils.resource_manager import available_contracts
from utils.contracts_utils import verify_bytecode, proof_validator
import logging


class RelayerManager():
    def __init__(self, address: str, port: int, chain_id: int):
        self.address = address
        self.port = port
        self.chain_id = chain_id
        self.server = SimpleXMLRPCServer((self.address, self.port))
        self.server.register_function(self.remap_relayer, "remap_relayer")
        self.server.serve_forever()
        self.relayer = CBWrapper()

    def _bytecode_matches(self, src_endpoint: str, src_addrs: List[str]):
        contracts = available_contracts(self.chain_id, None)
        dst_addrs = [contracts[type].address for type in contracts]
        return verify_bytecode([src_endpoint, "http://"+self.address+":8545"], src_addrs, dst_addrs)

    def _storage_integrity(self):
        return proof_validator()

    def remap_relayer(self, src_endpoint: str, from_block: int, src_addrs: str):
        logging.info("User asked for relayer remapping: %s, %i" %
                     (src_endpoint, from_block))
        # Check conditions for remapping relayer
        if self._bytecode_matches(src_endpoint, src_addrs) and self._storage_integrity():
            if self.relayer.is_relayer_running():
                self.relayer.stop_relay()
            else:
                # TODO: Write new endpoints in db
                self.relayer.start_relay(latest=from_block)
            return {"response": "OK",
                    "extra": "We are parsing your events."}
        else:
            return {"response": "NOK",
                    "extra": "Your contract bytecode is different or smart contract storage has different transactions."}


if __name__ == '__main__':
    srv = RelayerManager("192.168.1.110", 23456, 100)
