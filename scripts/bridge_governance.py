from typing import List
from web3 import HTTPProvider, Web3
from web3.middleware.geth_poa import geth_poa_middleware
from utils.contracts_utils import load_abi
from enum import Enum
import logging
import os
import json

SECRET_KEY_PATH = "resources/.secret"
PROPOSALS_BASE_PATH = "resources/proposals"
BRIDGE_ADDR = "0xAd28ab39509672F4D621206710654bd875D5fEa2"
BRIDGE_GOVERNANCE_ADDR = "0x8783E2Fdf8C04dFA64DFC15eba46Bebcc6296C1f"


class Vote(Enum):
    AGAINST = 0
    FOR = 1
    ABSTAIN = 2


class BridgeGovernance():
    def __init__(self, node_endpoint: Web3, bridge_governance_addr: str, bridge_addr: str = None):
        self.node_endpoint = node_endpoint
        self.node_endpoint.middleware_onion.inject(
            geth_poa_middleware, layer=0)
        self.bridge_governance_addr = bridge_governance_addr
        self.bridge_governance = self.node_endpoint.eth.contract(
            address=bridge_governance_addr, abi=load_abi("crosscoin/build/contracts/BridgeGovernance.json"))
        if bridge_addr != None:
            self.bridge = self.node_endpoint.eth.contract(
                address=bridge_addr, abi=load_abi("crosscoin/build/contracts/Bridge.json"))
        with open(SECRET_KEY_PATH) as f:
            key = f.readline().strip()
        self.account = self.node_endpoint.eth.account.from_key(
            key)

    def _call_function(self, function, amount: int = 0):
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
        return receipt

    def join_governance(self, address: str, amount: int):
        function = self.bridge_governance.functions.join(address)
        self._call_function(function, amount)

    def vote_proposal(self, proposal_id: int, vote: Vote):
        function = self.bridge_governance.functions.castVote(
            proposal_id, vote.value)
        self._call_function(function)

    # This command has some effect only if the function is called with the admin account
    def drop_priviledges(self):
        function = self.bridge.functions.renounceAdmin(
            self.bridge_governance_addr)
        self._call_function(function)

    def _make_proposal(self, calldata, resource_addresses: List[str], description: str):
        logging.info("calldata is:" + str(calldata))
        function = self.bridge_governance.functions.propose(
            [self.bridge.address], [0], [calldata], description)
        receipt = self._call_function(function)
        if receipt["status"] == 1:
            event = bridge.bridge_governance.events.ProposalCreated.getLogs(
                fromBlock=receipt["blockNumber"])
            proposal_id = str(event[0]["args"]["proposalId"])
            proposal = {"proposal_id": proposal_id,
                        "targets": resource_addresses, "values": [0],
                        "description": description, }
            with open(os.path.join(PROPOSALS_BASE_PATH, proposal_id + ".json"), "w") as f:
                json.dump(obj=proposal, fp=f)
            logging.info("Your proposal id is: " + str(proposal_id))
            return int(proposal_id)
        else:
            logging.info(
                "Status is 0, you may have not the priviledges for this action or the proposal was issued previously.")

    def execute_proposal(self, proposal_id: int):
        pass

    def remap_proposal(self, resource_addresses: List[str], description: str):
        calldata = self.bridge.encodeABI(
            fn_name="adminSetResource", args=resource_addresses)
        return self._make_proposal(calldata, resource_addresses, description)
        


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    node = Web3(HTTPProvider("http://192.168.1.110:8545"))
    bridge = BridgeGovernance(
        node, BRIDGE_GOVERNANCE_ADDR, BRIDGE_ADDR)
    proposal_id = bridge.remap_proposal(
        [BRIDGE_ADDR, "0xd8de56dd1db472be57d5840cb8d8d5961c69601e8d8d8a0c97a57c9ae8cb0f0f", BRIDGE_ADDR], "test")
    bridge.vote_proposal(
        proposal_id, Vote.FOR)
