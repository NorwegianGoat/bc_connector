import unittest
from utils.truffle_utils import Truffle
from bridge_governance import BridgeGovernance, Vote
from web3 import Web3, HTTPProvider
from utils.resource_manager import add_contract
from model.contract import ContractTypes
import time
import relayer_client
from threading import Thread
from relayer_manager import RelayerManager
from utils.cc_redeem import redeem_tokens
import os
from utils.cb_wrapper import CBWrapper


NODE0_ENDPOINT = "http://192.168.1.110:8545"
NODE1_ENDPOINT = "http://192.168.1.120:8545"
PKEY_PATH = 'resources/.secret'
TRUDY_PKEY_PATH = 'resources/.tsecret'
WAIT = 20
RES_ID = "0xd8de56dd1db472be57d5840cb8d8d5961c69601e8d8d8a0c97a57c9ae8cb0f0f"


class TestPatches(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Deploy contracts and config chains
        deployer = Truffle("goatchain0")
        cls.contracts_n0 = deployer.run_migration(9, 9)
        deployer = Truffle("goatchain1")
        cls.contracts_n1_wrong = deployer.run_migration(9, 9)
        deployer = Truffle("goatchain1")
        cls.contracts_n1_good = deployer.run_migration(9, 9)
        # Configure node and saving deployed data
        cls.n0 = Web3(HTTPProvider(NODE0_ENDPOINT))
        cls.n1_wrong = Web3(HTTPProvider(NODE1_ENDPOINT))
        cls.n1_good = Web3(HTTPProvider(NODE1_ENDPOINT))
        add_contract(ContractTypes.BRIDGE.value,
                     cls.contracts_n0[1], cls.n0.eth.chain_id, int(time.time()))
        add_contract(ContractTypes.ERC20_HANDLER.value,
                     cls.contracts_n0[2], cls.n0.eth.chain_id, int(time.time()))
        add_contract(ContractTypes.ERC20.value,
                     cls.contracts_n0[0], cls.n0.eth.chain_id, int(time.time()))
        add_contract(ContractTypes.BRIDGE.value,
                     cls.contracts_n1_good[1], cls.n1_good.eth.chain_id, int(time.time()))
        add_contract(ContractTypes.ERC20_HANDLER.value,
                     cls.contracts_n1_good[2], cls.n1_good.eth.chain_id, int(time.time()))
        add_contract(ContractTypes.ERC20.value,
                     cls.contracts_n1_good[0], cls.n1_good.eth.chain_id, int(time.time()))
        # Configuring test accounts
        with open(PKEY_PATH) as f:
            key = f.readline().strip()
        cls.alice = cls.n0.eth.account.from_key(key)
        cls.governance_n0 = BridgeGovernance(cls.alice,
                                             cls.n0, cls.contracts_n0[-1], cls.contracts_n0[1])
        cls.governance_n1_wrong = BridgeGovernance(cls.alice,
                                                   cls.n1_wrong, cls.contracts_n1_wrong[-1], cls.contracts_n1_wrong[-1])
        cls.governance_n1_good = BridgeGovernance(cls.alice,
                                                  cls.n1_good, cls.contracts_n1_good[-1], cls.contracts_n1_good[1])
        with open(TRUDY_PKEY_PATH) as f:
            key = f.readline().strip()
        cls.trudy = cls.n0.eth.account.from_key(key)
        # Drop admin privileges and give them to the governance
        cls.governance_n0.drop_priviledges()
        cls.governance_n1_wrong.drop_priviledges()
        cls.governance_n1_good.drop_priviledges()
        # Configure chain 1 bridges
        proposal_id = cls.governance_n1_good.remap_proposal([cls.contracts_n1_good[0], RES_ID,
                                                             cls.contracts_n1_good[2]],
                                                            "This is a good mapping.")
        cls.governance_n1_good.vote_proposal(proposal_id, Vote.FOR)
        time.sleep(WAIT)
        receipt = cls.governance_n1_good.execute_proposal(proposal_id)
        proposal_id = cls.governance_n1_wrong.remap_proposal([cls.contracts_n1_wrong[0], RES_ID,
                                                              cls.contracts_n1_wrong[1]],
                                                             "This is a wrong mapping.")
        cls.governance_n1_wrong.vote_proposal(proposal_id, Vote.FOR)
        time.sleep(WAIT)
        receipt = cls.governance_n1_wrong.execute_proposal(proposal_id)
        # Generate some deposits on chain 1
        redeem_tokens(cls.n1_good, cls.alice, 1, ContractTypes.ERC20)
        cls.cb_wrapper = CBWrapper()
        cls.cb_wrapper.deposit("http://192.168.1.120:8545", cls.alice.key, 10,
                               ContractTypes.ERC20, 1, 100, cls.contracts_n1_good[1], cls.alice.address, RES_ID)
        # Start relayer server
        thread = Thread(target=RelayerManager, args=(
            "http://192.168.1.110", 23456, NODE0_ENDPOINT, cls.contracts_n0[3]))
        thread.start()
        #subprocess.run(['nohup', 'python3', 'relayer_manager.py', '&'])

    # A non admin user should not be able to make a proposal
    def test_00proposalNonAdmin(self):
        # test with trudy
        TestPatches.governance_n0.set_account(TestPatches.trudy)
        proposal_id = TestPatches.governance_n0.add_relayer_proposal(
            [TestPatches.trudy.address], "Add me as relayer pls.")
        TestPatches.governance_n0.set_account(TestPatches.alice)
        self.assertIsNone(proposal_id)

    # An user which is an admin should be able to make a proposal
    def test_01proposalAdmin(self):
        proposal_id = TestPatches.governance_n0.add_relayer_proposal(
            [TestPatches.trudy.address], "Add Trudy as relayer.")
        self.assertIsNotNone(proposal_id)

    # Tries to execute a proposal which has not met the quorum. Should fail.
    def test_02executeProposalNoQuorum(self):
        # Join the governance with the second account
        TestPatches.governance_n0.set_account(TestPatches.trudy)
        receipt = TestPatches.governance_n0.join_governance(
            TestPatches.trudy.address, 1000000000000000000)
        proposal_id = TestPatches.governance_n0.remap_proposal(["0xCC08eac119e25f6E365C25d61eA60bC8e74B681e", RES_ID,
                                                                "0x3ab2A28A2a95FA7bbBdF8DfED9e6D945E99dDf38"],
                                                               "I promise that this mapping is good!")
        TestPatches.governance_n0.vote_proposal(proposal_id, Vote.FOR)
        # Wait 10 blocks
        time.sleep(WAIT)
        receipt = TestPatches.governance_n0.execute_proposal(proposal_id)
        TestPatches.governance_n0.set_account(TestPatches.alice)
        self.assertEqual(receipt['status'], 0)

    # Executes a proposal which has met the quorum and is passed
    def test_03executeProposalQuorum(self):
        proposal_id = TestPatches.governance_n0.remap_proposal([TestPatches.contracts_n0[0], RES_ID,
                                                                TestPatches.contracts_n0[2]],
                                                               "This is a good mapping.")
        TestPatches.governance_n0.vote_proposal(proposal_id, Vote.FOR)
        TestPatches.governance_n0.set_account(TestPatches.trudy)
        TestPatches.governance_n0.vote_proposal(proposal_id, Vote.FOR)
        TestPatches.governance_n0.set_account(TestPatches.alice)
        time.sleep(WAIT)
        receipt = TestPatches.governance_n0.execute_proposal(proposal_id)
        self.assertEqual(receipt['status'], 1)

    # Tries to execute a proposal which is not passed. Should fail.
    def test_04executeProposalNotPassed(self):
        proposal_id = TestPatches.governance_n0.add_relayer_proposal(
            ["0xF5a1AB745E1E9AB203bB28d397C12D2840256dff"], "Let's add this other random address as relayer!")
        TestPatches.governance_n0.vote_proposal(proposal_id, Vote.FOR)
        TestPatches.governance_n0.set_account(TestPatches.trudy)
        TestPatches.governance_n0.vote_proposal(proposal_id, Vote.AGAINST)
        TestPatches.governance_n0.set_account(TestPatches.alice)
        time.sleep(WAIT)
        receipt = TestPatches.governance_n0.execute_proposal(proposal_id)
        self.assertEqual(receipt['status'], 0)

    # A relayer ask for remap. Good storage.
    def test_05askRemapGoodStorage(self):
        history = "resources/contract_storage_tries/45.json"
        if os.path.exists(history):
            os.remove(history)
        response = relayer_client.ask_remap(
            "http://192.168.1.110:23456", "http://192.168.1.120:8545",
            TestPatches.n1_good.eth.get_block("latest")['number']-1000, TestPatches.contracts_n1_good[1], RES_ID)
        self.assertEqual(response["response"], "OK")

    # A relayer ask for a remap, but his storage is wrong. Should fail.
    def test_06askRemapWrongStorage(self):
        pass

    # A relayer ask for remap. Smart contract code is not equal. Should fail.
    def test_07askRemapWrongCode(self):
        pass

    # A relayer ask for remap, smart contract code matches. Should pass.
    def test_08askRemapGoodCode(self):
        pass

    # Admin tries to refund an user sending wrong data to the smart contract. Should fail.
    def test_09refundWrongData(self):
        pass

    # Admin tries to refund an user sending good data to the smart contract.
    def test_10refundGoodData(self):
        pass

    # Admin withdraws the fee to early. Should fail.
    def test_11withdrawFeeTooEarly(self):
        pass

    # Admin whithdraw the fee after waiting enough time.
    def test_12withdrawFee(self):
        pass


if __name__ == "__main__":
    unittest.main()
