import unittest
from utils.truffle_utils import Truffle
from bridge_governance import BridgeGovernance, Vote
from web3 import Web3, HTTPProvider
import time


NODE0_ENDPOINT = "http://192.168.1.110:8545"
PKEY_PATH = 'resources/.secret'
TRUDY_PKEY_PATH = 'resources/.tsecret'
WAIT = 20


class TestPatches(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Deploy contracts
        deployer = Truffle("goatchain0")
        cls.contracts = deployer.run_migration(9, 9)
        # Configure node
        cls.n0 = Web3(HTTPProvider(NODE0_ENDPOINT))
        # Configuring test accounts
        with open(PKEY_PATH) as f:
            key = f.readline().strip()
        cls.alice = cls.n0.eth.account.from_key(key)
        cls.governance = BridgeGovernance(cls.alice,
                                          cls.n0, cls.contracts[-1], cls.contracts[1])
        with open(TRUDY_PKEY_PATH) as f:
            key = f.readline().strip()
        cls.trudy = cls.n0.eth.account.from_key(key)
        # Drop admin privileges and give them to the governance
        cls.governance.drop_priviledges()

    # A non admin user should not be able to make a proposal
    def test_0proposalNonAdmin(self):
        # test with trudy
        TestPatches.governance.set_account(TestPatches.trudy)
        proposal_id = TestPatches.governance.add_relayer_proposal(
            [TestPatches.trudy.address], "Add me as relayer pls.")
        TestPatches.governance.set_account(TestPatches.alice)
        self.assertIsNone(proposal_id)

    # An user which is an admin should be able to make a proposal
    def test_1proposalAdmin(self):
        proposal_id = TestPatches.governance.add_relayer_proposal(
            [TestPatches.trudy.address], "Add Trudy as relayer.")
        self.assertIsNotNone(proposal_id)

    # Tries to execute a proposal which has not met the quorum. Should fail.
    def test_2executeProposalNoQuorum(self):
        # Join the governance with the second account
        TestPatches.governance.set_account(TestPatches.trudy)
        receipt = TestPatches.governance.join_governance(
            TestPatches.trudy.address, 1000000000000000000)
        proposal_id = TestPatches.governance.remap_proposal(["0xCC08eac119e25f6E365C25d61eA60bC8e74B681e", "0xd8de56dd1db472be57d5840cb8d8d5961c69601e8d8d8a0c97a57c9ae8cb0f0f",
                                                             "0x3ab2A28A2a95FA7bbBdF8DfED9e6D945E99dDf38"],
                                                            "I promise that this mapping is good!")
        TestPatches.governance.vote_proposal(proposal_id, Vote.FOR)
        # Wait 10 blocks
        time.sleep(WAIT)
        receipt = TestPatches.governance.execute_proposal(proposal_id)
        TestPatches.governance.set_account(TestPatches.alice)
        self.assertEqual(receipt['status'], 0)

    # Executes a proposal which has met the quorum and is passed
    def test_3executeProposalQuorum(self):
        proposal_id = TestPatches.governance.add_relayer_proposal(
            ["0xFb3a2e25724D42b982634Dd060A026C458d67418"], "Let's add this random address as relayer!")
        TestPatches.governance.vote_proposal(proposal_id, Vote.FOR)
        TestPatches.governance.set_account(TestPatches.trudy)
        TestPatches.governance.vote_proposal(proposal_id, Vote.FOR)
        TestPatches.governance.set_account(TestPatches.alice)
        time.sleep(WAIT)
        receipt = TestPatches.governance.execute_proposal(proposal_id)
        self.assertEqual(receipt['status'], 1)

    # Tries to execute a proposal which is not passed. Should fail.
    def test_4executeProposalNotPassed(self):
        proposal_id = TestPatches.governance.add_relayer_proposal(
            ["0xF5a1AB745E1E9AB203bB28d397C12D2840256dff"], "Let's add this other random address as relayer!")
        TestPatches.governance.vote_proposal(proposal_id, Vote.FOR)
        TestPatches.governance.set_account(TestPatches.trudy)
        TestPatches.governance.vote_proposal(proposal_id, Vote.AGAINST)
        TestPatches.governance.set_account(TestPatches.alice)
        time.sleep(WAIT)
        receipt = TestPatches.governance.execute_proposal(proposal_id)
        self.assertEqual(receipt['status'], 0)

    # A relayer ask for a remap, but his storage is wrong. Should fail.
    def test_askRemapWrongStorage(self):
        pass

    # A relayer ask for remap. Good storage.
    def test_askRemapGoodStorage(self):
        pass

    # A relayer ask for remap. Smart contract code is not equal. Should fail.
    def test_askRemapWrongCode(self):
        pass

    # A relayer ask for remap, smart contract code matches. Should pass.
    def test_askRemapGoodCode(self):
        pass

    # Admin tries to refund an user sending wrong data to the smart contract. Should fail.
    def test_refundWrongData(self):
        pass

    # Admin tries to refund an user sending good data to the smart contract.
    def test_refundGoodData(self):
        pass

    # Admin withdraws the fee to early. Should fail.
    def test_withdrawFeeTooEarly(self):
        pass

    # Admin whithdraw the fee after waiting enough time.
    def test_withdrawFee(self):
        pass


if __name__ == "__main__":
    unittest.main()
