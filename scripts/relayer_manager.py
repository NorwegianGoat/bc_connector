from typing import List
from xmlrpc.server import SimpleXMLRPCServer
from utils.cb_wrapper import CBWrapper
from utils.resource_manager import available_contracts
from utils.contracts_utils import verify_bytecode, proof_validator
import logging


ADDRESS = "192.168.1.3"
PORT = 23456
# The chain id of the blockchain of this relayer
CHAIN_ID = 100


def _bytecode_matches(src_endpoint: str, src_addrs: List[str]):
    contracts = available_contracts(CHAIN_ID, None)
    dst_addrs = [contracts[type].address for type in contracts]
    return verify_bytecode([src_endpoint, "http://"+ADDRESS+":8545"], src_addrs, dst_addrs)


def _storage_integrity():
    return proof_validator()


def remap_relayer(src_endpoint: str, from_block: int, src_addrs: str):
    logging.info("User asked for relayer remapping: %s, %i" %
                 (src_endpoint, from_block))
    # Check conditions for remapping relayer
    if _bytecode_matches(src_endpoint, src_addrs) and _storage_integrity():
        if cb.is_relayer_running():
            cb.stop_relay()
        else:
            # TODO: Write new endpoints in db
            cb.start_relay(latest=from_block)
        return {"response": "OK",
                "extra": "We are parsing your events."}
    else:
        return {"response": "NOK",
                "extra": "Your contract bytecode is different or smart contract storage has different transactions."}


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    server = SimpleXMLRPCServer((ADDRESS, PORT))
    server.register_function(remap_relayer, "remap_relayer")
    server.serve_forever()
    cb = CBWrapper()
