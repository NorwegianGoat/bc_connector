from model.contract import ContractTypes
from xmlrpc.server import SimpleXMLRPCServer
from utils.cb_wrapper import CBWrapper
from utils.resource_manager import available_contracts, add_contract
from utils.contracts_utils import proof_maker, verify_bytecode, trie_maker, TRIES_BASEPATH, load_abi
from web3 import Web3, HTTPProvider
import logging
import os
import json
import time
from merkletools import MerkleTools

SECRET_KEY_PATH = "resources/.secret"
CONTRACT_ABIS = "crosscoin/build/contracts"
# This is the address of the local root board (the contract in which the root state is committed)
LOCAL_BOARD = "0x7834bCF13119474873E1BFA4ea588A8AfD79a69F"
NODE_IP = "192.168.1.110"
NODE_ENDPOINT = "http://"+NODE_IP+":8545"


class RelayerManager():
    def __init__(self, address: str, port: int, dst_endpoint: str, local_board: str = LOCAL_BOARD):
        # Blockchain nodes and contracts
        self.src_endpoint = None
        self.dst_endpoint = Web3(HTTPProvider(dst_endpoint))
        self.src_addrs = None
        self.dst_addrs = None
        self.local_board = local_board
        # Root board writer admin account
        with open(SECRET_KEY_PATH) as f:
            key = f.readline().strip()
        self.relayer_admin_account = self.dst_endpoint.eth.account.from_key(
            key)
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
        return verify_bytecode([self.src_endpoint.provider.endpoint_uri, self.dst_endpoint.provider.endpoint_uri], self.src_addrs, self.dst_addrs)
        # return True # Just for test puposes

    def _get_root(self):
        board_abi = load_abi(os.path.join(CONTRACT_ABIS, "RootBoard.json"))
        board = self.dst_endpoint.eth.contract(
            abi=board_abi, address=self.local_board)
        return board.functions.getLatestRoot(
            self.src_endpoint.eth.chain_id).call()

    def _write_root(self, nonce: int, root: str):
        board_abi = load_abi(os.path.join(CONTRACT_ABIS, "RootBoard.json"))
        board = self.dst_endpoint.eth.contract(
            abi=board_abi, address=self.local_board)
        # Fire redeem transaction
        t_dict = {"chainId": self.dst_endpoint.eth.chain_id,
                  "nonce": self.dst_endpoint.eth.get_transaction_count(self.relayer_admin_account.address, 'pending'),
                  "gasPrice": self.dst_endpoint.toWei(10, "gwei"),
                  "gas": 1000000}
        tx = board.functions.setLatestRoot(self.src_endpoint.eth.chain_id,
                                           nonce, root).buildTransaction(t_dict)
        signed_tx = self.dst_endpoint.eth.account.sign_transaction(
            tx, self.relayer_admin_account.key)
        tx_hash = self.dst_endpoint.eth.send_raw_transaction(
            signed_tx.rawTransaction)
        receipt = self.dst_endpoint.eth.wait_for_transaction_receipt(tx_hash)
        logging.info("root update tx_receipt: " + str(receipt))
        return receipt['status']

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
            chain_root = self._get_root()
            if trie.get_merkle_root() == chain_root[1]:
                logging.info("Our root matches match with the one saved on chain. " +
                             trie.get_merkle_root() + " vs. " + str(chain_root))
            else:
                logging.info("Our root does not match with the one saved on chain. " +
                             trie.get_merkle_root() + " vs. " + str(chain_root))
                return False
            # Read the storage on source chain and generate a proof for the last
            # deposit then check the proof against our saved trie
            latest_nonce_saved = int(saved_trie["deposits"][-1]['nonce'])
            user_trie = trie_maker(
                self.src_endpoint, self.dst_endpoint, self.src_addrs[0], latest_nonce_saved)
            proof = proof_maker(user_trie, latest_nonce_saved)
            if trie.validate_proof(proof[0], proof[1], trie.get_merkle_root()):
                logging.info("Proof is compatible!")
            else:
                logging.info("The proof is not compatible with our root!")
                return False
        # We log the contract used
        add_contract(ContractTypes.BRIDGE.value,
                     self.src_addrs[0], self.src_endpoint.eth.chain_id, int(time.time()))
        add_contract(ContractTypes.ERC20_HANDLER.value,
                     self.src_addrs[1], self.src_endpoint.eth.chain_id, int(time.time()))
        add_contract(ContractTypes.ERC20.value,
                     self.src_addrs[2], self.src_endpoint.eth.chain_id, int(time.time()))
        # Write the updated root on chain
        trie = trie_maker(
            self.src_endpoint, self.dst_endpoint, self.src_addrs[0], save_on_disk=True)
        with open(trie_path) as f:
            saved_trie = json.load(fp=f)
        result = self._write_root(saved_trie["deposits"][-1]
                                  ["nonce"], trie.get_merkle_root())
        if not result:
            logging.info("Unable to write root in smart contract. Same nonce.")
            return False
        else:
            return True

    def remap_relayer(self, src_endpoint: str, from_block: int, src_bridge_addr: str, res_id: str):
        self.src_endpoint = Web3(HTTPProvider(src_endpoint))
        logging.info("User asked for remapping the relayer: %s, %i, %i" %
                     (src_endpoint, self.src_endpoint.eth.chain_id, from_block))
        self._get_addrs(src_bridge_addr, res_id)
        # Check conditions for remapping the relayer
        if self._bytecode_matches() and self._storage_integrity():
            if self.relayer.is_relayer_running():
                self.relayer.stop_relay()
            self.relayer.update_config_json(
                self.dst_endpoint, ContractTypes.ERC20)
            self.relayer.start_relay(latest=from_block)
            return {"response": "OK",
                    "extra": "We are parsing your events."}
        else:
            return {"response": "NOK",
                    "extra": "Errors in bytecode verification or in storage probing phase."}


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    srv = RelayerManager(NODE_IP, 23456, NODE_ENDPOINT)
