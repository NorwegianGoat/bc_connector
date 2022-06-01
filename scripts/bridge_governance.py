from typing import List
from web3 import HTTPProvider, Web3
from web3.middleware.geth_poa import geth_poa_middleware
from utils.contracts_utils import load_abi
from enum import Enum
import logging
import os
import json
import time

SECRET_KEY_PATH = "resources/.secret"
PROPOSALS_BASE_PATH = "resources/proposals"
BRIDGE_ADDR = "0x63Eef9C40ab428CD48Be40Bc2517b168f67B750f"
BRIDGE_GOVERNANCE_ADDR = "0x0A03fBe04D9cd154052db3394393Ca690096BAE0"


class Vote(Enum):
    AGAINST = 0
    FOR = 1
    ABSTAIN = 2


class BridgeGovernance():
    def __init__(self, account, node_endpoint: Web3, bridge_governance_addr: str, bridge_addr: str = None):
        self.node_endpoint = node_endpoint
        self.node_endpoint.middleware_onion.inject(
            geth_poa_middleware, layer=0)
        self.bridge_governance_addr = bridge_governance_addr
        self.bridge_governance = self.node_endpoint.eth.contract(
            address=bridge_governance_addr, abi=load_abi("crosscoin/build/contracts/BridgeGovernance.json"))
        if bridge_addr != None:
            self.bridge = self.node_endpoint.eth.contract(
                address=bridge_addr, abi=load_abi("crosscoin/build/contracts/Bridge.json"))
        self.account = account

    def set_account(self, account):
        self.account = account

    def _call_function(self, function, amount: int = 0):
        t_dict = {"chainId": self.node_endpoint.eth.chain_id,
                  "value": amount,
                  "nonce": self.node_endpoint.eth.get_transaction_count(self.account.address, 'pending'),
                  "gasPrice": self.node_endpoint.toWei(1, "gwei"),
                  "gas": 1000000}
        tx = function.buildTransaction(t_dict)
        signed_tx = self.node_endpoint.eth.account.sign_transaction(
            tx, self.account.key)
        tx_hash = self.node_endpoint.eth.send_raw_transaction(
            signed_tx.rawTransaction)
        receipt = self.node_endpoint.eth.wait_for_transaction_receipt(tx_hash)
        logging.info("tx_receipt: " + str(receipt))
        return receipt

    # Specify an account to be added to the governance
    def join_governance(self, address: str, amount: int):
        function = self.bridge_governance.functions.join(address)
        return self._call_function(function, amount)

    # Proposal lifecycle functions: vote, make and execute
    def vote_proposal(self, proposal_id: int, vote: Vote):
        function = self.bridge_governance.functions.castVote(
            proposal_id, vote.value)
        return self._call_function(function)

    def _make_proposal(self, targets: List[str], amount: List[int], calldata: List[str], description: str):
        logging.info("calldata is:" + str(calldata))
        function = self.bridge_governance.functions.propose(
            targets, amount, calldata, description)
        receipt = self._call_function(function)
        if receipt["status"] == 1:
            event = self.bridge_governance.events.ProposalCreated.getLogs(
                fromBlock=receipt["blockNumber"])
            proposal_id = str(event[0]["args"]["proposalId"])
            proposal = {"proposal_id": proposal_id,
                        "targets": targets, "values": amount,
                        "calldata": calldata,
                        "description": description,
                        "description_hash": Web3.keccak(text=description).hex()}
            with open(os.path.join(PROPOSALS_BASE_PATH, proposal_id + ".json"), "w") as f:
                json.dump(obj=proposal, fp=f)
            logging.info("Your proposal id is: " + str(proposal_id))
            return int(proposal_id)
        else:
            logging.info(
                "Status is 0, you may have not the priviledges for this action or the proposal was issued previously.")

    def execute_proposal(self, proposal_id: int):
        with open(os.path.join(PROPOSALS_BASE_PATH, str(proposal_id) + ".json")) as f:
            proposal = json.load(fp=f)
        logging.info(proposal["targets"], proposal["values"],
                     proposal["calldata"], proposal["description_hash"])
        function = self.bridge_governance.functions.execute(
            proposal["targets"], proposal["values"], proposal["calldata"], proposal["description_hash"])
        return self._call_function(function)

    # This command has some effect only if the function is called with the admin account
    # It drops priviledges on the bridge from the individual and it gives them to the
    # bridge governance account.
    def drop_priviledges(self):
        function = self.bridge.functions.renounceAdmin(
            self.bridge_governance_addr)
        self._call_function(function)

    def remap_proposal(self, resource_addresses: List[str], description: str):
        calldata = self.bridge.encodeABI(
            fn_name="adminSetResource", args=resource_addresses)
        return self._make_proposal([self.bridge.address], [0], [calldata], description)

    def add_relayer_proposal(self, relayer_address: str, description: str):
        calldata = self.bridge.encodeABI(
            fn_name="adminAddRelayer", args=relayer_address)
        return self._make_proposal([self.bridge.address], [0], [calldata], description)

    def rm_relayer_proposal(self, relayer_address: str, description):
        calldata = self.bridge.encodeABI(
            fn_name="adminRemoveRelayer", args=relayer_address)
        return self._make_proposal([self.bridge.address], [0], [calldata], description)

    def change_relayer_threshold_proposal(self, relayer_threshold: int, description: str):
        calldata = self.bridge.encodeABI(
            fn_name="adminRelayerThreshold", args=relayer_threshold)
        return self._make_proposal([self.bridge.address], [0], [calldata], description)

    def pause_bridge_proposal(self, description):
        calldata = self.bridge.encodeABI(
            fn_name="adminPauseTransfers")
        return self._make_proposal([self.bridge.address], [0], [calldata], description)

    def unpause_bridge_proposal(self, description):
        calldata = self.bridge.encodeABI(
            fn_name="adminUnpauseTransfers")
        return self._make_proposal([self.bridge.address], [0], [calldata], description)

    def withdraw_fee_proposal(self, description):
        # TODO: ENCODING PARAMETERS
        calldata = self.bridge.encodeABI(
            fn_name="")
        return self._make_proposal([self.bridge.address], [0], [calldata], description)

    def refund_user_proposal(self, chain_id:int, deposit_id:int, handler_address: str, data, description):
        calldata = self.bridge.encodeABI(
            fn_name="adminWithdraw", args=[chain_id, deposit_id, handler_address, data])
        return self._make_proposal([self.bridge.address], [0], [calldata], description)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    node = Web3(HTTPProvider("http://192.168.1.110:8545"))
    bridge = BridgeGovernance(
        node, BRIDGE_GOVERNANCE_ADDR, BRIDGE_ADDR)
    ''' 
    # Tests
    # Handler, resource id, token
    proposal_id = bridge.remap_proposal(
        ["0xCC08eac119e25f6E365C25d61eA60bC8e74B681e", "0xd8de56dd1db472be57d5840cb8d8d5961c69601e8d8d8a0c97a57c9ae8cb0f0f",
            "0x3ab2A28A2a95FA7bbBdF8DfED9e6D945E99dDf38"],
        "Let's map the bridge! Again!")
    bridge.vote_proposal(proposal_id, Vote.FOR)
    bridge.drop_priviledges()
    time.sleep(20)
    bridge.execute_proposal(proposal_id)
    '''
