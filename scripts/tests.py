import unittest
from utils.truffle_utils import Truffle
from bridge_governance import BridgeGovernance, Vote
from web3 import Web3, HTTPProvider


NODE0_ENDPOINT = "http://192.168.1.110:8545"
PKEY_PATH = 'resources/.secret'
TRUDY_PKEY_PATH = 'resources/.tsecret'


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
        response = TestPatches.governance.add_relayer_proposal(
            [TestPatches.trudy.address], "Add me as relayer pls.")
        TestPatches.governance.set_account(TestPatches.alice)
        self.assertIsNone(response)

    # An user which is an admin should be able to make a proposal

    def test_1proposalAdmin(self):
        response = TestPatches.governance.add_relayer_proposal(
            [TestPatches.trudy.address], "Add Trudy as relayer.")
        self.assertIsNotNone(response)

    # Tries to execute a proposal which has not met the quorum. Should fail.
    def test_2executeProposalNoQuorum(self):
        # Join the governance with the second account
        TestPatches.governance.set_account(TestPatches.trudy)
        receipt = TestPatches.governance.join_governance(
            TestPatches.trudy.address, 1000000000000000000)
        response = TestPatches.governance.remap_proposal(["0xCC08eac119e25f6E365C25d61eA60bC8e74B681e", "0xd8de56dd1db472be57d5840cb8d8d5961c69601e8d8d8a0c97a57c9ae8cb0f0f",
                                                           "0x3ab2A28A2a95FA7bbBdF8DfED9e6D945E99dDf38"],
                                                         "I promise that this mapping is good!")
        TestPatches.governance.vote_proposal(response, Vote.FOR)
        receipt = TestPatches.governance.execute_proposal(response)
        self.assertEqual(receipt['status'], 0)

    # Executes a proposal which has met the quorum.
    def test_executoeProposalQuorum(self):
        pass

    # Tries to execute a proposal which is not passed. Should fail.
    def test_executeProposalNotPassed(self):
        pass

    # Tries to execute a proposal which is passed. Should pass.
    def test_executeProposalPassed(self):
        pass

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
