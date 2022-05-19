from typing import List
from web3 import Web3
from utils.contracts_utils import load_abi
import logging

SECRET_KEY_PATH = "resources/.secret"
BRIDGE_ADDR = "0xAd28ab39509672F4D621206710654bd875D5fEa2"


class BridgeGovernance():
    def __init__(self, node_endpoint: Web3, bridge_governance_addr: str, bridge_addr: str = None):
        self.node_endpoint = node_endpoint
        self.bridge_governance_addr = bridge_governance_addr
        self.bridge_governance = self.node_endpoint.eth.contract(
            address=bridge_governance_addr, abi=load_abi("crosscoin/build/BridgeGovernance.json"))
        if bridge_addr != None:
            self.bridge = self.node_endpoint.eth.contract(
                address=bridge_addr, abi=load_abi("crosscoin/build/Bridge.json"))
        with open(SECRET_KEY_PATH) as f:
            key = f.readline().strip()
        self.account = self.node_endpoint.eth.account.from_key(
            key)

    def _call_function(self, function, amount: int = 0):
        # Fire redeem transaction
        t_dict = {"chainId": self.node_endpoint.eth.chain_id,
                  "nonce": self.node_endpoint.eth.get_transaction_count(self.account.address, 'pending'),
                  "gasPrice": self.node_endpoint.toWei(10, "gwei"),
                  "gas": 1000000}
        tx = function.buildTransaction(t_dict)
        signed_tx = self.node_endpoint.eth.account.sign_transaction(
            tx, self.account.key)
        tx_hash = self.node_endpoint.eth.send_raw_transaction(
            signed_tx.rawTransaction)
        receipt = self.node_endpoint.eth.wait_for_transaction_receipt(tx_hash)
        logging.info("root update tx_receipt: " + str(receipt))
        return receipt['status']

    def join_governance(self, amount: int):
        function = self.bridge_governance.functions.join(self.account.address)
        logging.info(self._call_function(function, amount))

    def vote_proposal():
        pass

    # This command has some effect only if the function is called with the admin account
    def drop_priviledges(self):
        function = self.bridge.functions.renounceAdmin(
            self.bridge_governance_addr)
        logging.info(self._call_function(function))

    def remap_proposal(self, resource_addresses=List[str]):
        calldata = self.bridge_governance.encodeAbi(fn_name="adminSetResource", args=resource_addresses)
        logging.info(calldata)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bridge = BridgeGovernance()
