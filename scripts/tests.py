import unittest
from utils.truffle_utils import Truffle
from model.node import Node


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
        cls.n0 = Node(NODE0_ENDPOINT)
        # Configuring test accounts
        with open(PKEY_PATH) as f:
            key = f.readline().strip()
        cls.alice = cls.n0.provider.eth.account.from_key(key)
        with open(TRUDY_PKEY_PATH) as f:
            key = f.readline().strip()
        cls.trudy = cls.n0.provider.eth.account.from_key(key)
        # Drop admin privileges and give them to the governance
        
        # Join the governance with the second account

    # A non admin user should not be able to make a proposal
    def test_proposalNonAdmin(self):
        self.assertEqual(None, None)
    
    # An user which is an admin should be able to make a proposal
    def test_proposalAdmin(self):
        pass

    # Tries to execute a proposal which has not met the quorum. Should fail.
    def test_executeProposalNoQuorum(self):
        pass

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
