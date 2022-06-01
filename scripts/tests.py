import unittest
from utils.truffle_utils import Truffle
from bridge_governance import BridgeGovernance, Vote
from web3 import Web3, HTTPProvider
from utils.resource_manager import add_contract, available_contracts, save_binding
from model.contract import ContractTypes
import time
import relayer_client
from multiprocessing import Process
from relayer_manager import RelayerManager
from utils.cc_redeem import redeem_tokens
import os
from utils.cb_wrapper import CBWrapper
from utils.sys_mod import ssh_helper


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
        cls.contracts_n1 = deployer.run_migration(9, 9)
        # Configure node and saving deployed data
        cls.n0 = Web3(HTTPProvider(NODE0_ENDPOINT))
        cls.n1 = Web3(HTTPProvider(NODE1_ENDPOINT))
        add_contract(ContractTypes.BRIDGE.value,
                     cls.contracts_n0[1], cls.n0.eth.chain_id, int(time.time()))
        add_contract(ContractTypes.ERC20_HANDLER.value,
                     cls.contracts_n0[2], cls.n0.eth.chain_id, int(time.time()))
        add_contract(ContractTypes.ERC20.value,
                     cls.contracts_n0[0], cls.n0.eth.chain_id, int(time.time()))
        contracts = available_contracts(100, ContractTypes.ERC20)
        save_binding(RES_ID, contracts['bridge'].id,
                     contracts['handler'].id, contracts['target'].id, 100)
        add_contract(ContractTypes.BRIDGE.value,
                     cls.contracts_n1[1], cls.n1.eth.chain_id, int(time.time()))
        add_contract(ContractTypes.ERC20_HANDLER.value,
                     cls.contracts_n1[2], cls.n1.eth.chain_id, int(time.time()))
        add_contract(ContractTypes.ERC20.value,
                     cls.contracts_n1[0], cls.n1.eth.chain_id, int(time.time()))
        contracts = available_contracts(45, ContractTypes.ERC20)
        save_binding(RES_ID, contracts['bridge'].id,
                     contracts['handler'].id, contracts['target'].id, 45)
        # Configuring test accounts
        with open(PKEY_PATH) as f:
            key = f.readline().strip()
        cls.alice = cls.n0.eth.account.from_key(key)
        cls.governance_n0 = BridgeGovernance(cls.alice,
                                             cls.n0, cls.contracts_n0[-1], cls.contracts_n0[1])
        cls.governance_n1 = BridgeGovernance(cls.alice,
                                             cls.n1, cls.contracts_n1[-1], cls.contracts_n1[1])
        with open(TRUDY_PKEY_PATH) as f:
            key = f.readline().strip()
        cls.trudy = cls.n0.eth.account.from_key(key)
        # Drop admin privileges and give them to the governance
        cls.governance_n0.drop_priviledges()
        cls.governance_n1.drop_priviledges()
        # Configure chain 1 bridges
        proposal_id = cls.governance_n1.remap_proposal([cls.contracts_n1[2], RES_ID,
                                                        cls.contracts_n1[0]],
                                                       "This is a good mapping.")
        cls.governance_n1.vote_proposal(proposal_id, Vote.FOR)
        time.sleep(WAIT)
        receipt = cls.governance_n1.execute_proposal(proposal_id)
        # Start relayer server and config cb wrapper
        cls.cb_wrapper = CBWrapper()
        cls.relayer_manager = Process(target=RelayerManager, args=(
            "192.168.1.110", 23456, NODE0_ENDPOINT, cls.contracts_n0[3]))
        cls.relayer_manager.start()

    @classmethod
    def tearDown(cls):
        cls.relayer_manager.terminate()

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
        proposal_id = TestPatches.governance_n0.remap_proposal([TestPatches.contracts_n0[2], RES_ID,
                                                                TestPatches.contracts_n0[0]],
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
    def test_05askRemapGoodStorageAndCode(self):
        # Generate some deposits on chain 1
        redeem_tokens(TestPatches.n1, TestPatches.alice,
                      TestPatches.n1.toWei(1, 'ether'), ContractTypes.ERC20)
        TestPatches.cb_wrapper.deposit("http://192.168.1.120:8545", TestPatches.alice.key.hex(), 1000000,
                                       ContractTypes.ERC20, TestPatches.n1.toWei(
                                           1, 'ether'), 100,
                                       TestPatches.contracts_n1[1], TestPatches.alice.address, RES_ID)
        history = "resources/contract_storage_tries/45.json"
        if os.path.exists(history):
            os.remove(history)
        response = relayer_client.ask_remap(
            "http://192.168.1.110:23456", "http://192.168.1.120:8545",
            TestPatches.n1.eth.get_block("latest")['number']-50, TestPatches.contracts_n1[1], RES_ID)
        self.assertEqual(response["response"], "OK")

    # A relayer ask for a remap, but his storage is wrong. Should fail.
    def test_06askRemapWrongStorage(self):
        CHAIN1 = ['192.168.1.120', '192.168.1.121',
                  '192.168.1.122', '192.168.1.123']
        redeem_tokens(TestPatches.n1, TestPatches.alice,
                      TestPatches.n1.toWei(1, 'ether'), ContractTypes.ERC20)
        for node in CHAIN1:
            ssh_helper(node, 'root', ['cd', 'edge_utils', '&&', 'python3', 'helper.py',
                                      'halt_node', '&&', 'python3', 'helper.py', 'backup', '--backup_name',
                                      'malicious_rollback', '--override', 'true', '&&', 'python3', 'helper.py', 'start_validator',
                                      '--ip', node, '1>/dev/null', '2>/dev/null'])
        TestPatches.cb_wrapper.deposit("http://192.168.1.120:8545", TestPatches.alice.key.hex(), 1000000,
                                       ContractTypes.ERC20, TestPatches.n1.toWei(
                                           1, 'ether'), 100,
                                       TestPatches.contracts_n1[1], TestPatches.alice.address, RES_ID)
        response = relayer_client.ask_remap(
            "http://192.168.1.110:23456", "http://192.168.1.120:8545",
            TestPatches.n1.eth.get_block("latest")['number']-50, TestPatches.contracts_n1[1], RES_ID)
        # Restore the old state
        for node in CHAIN1:
            ssh_helper(node, 'root', ['cd', 'edge_utils', '&&', 'python3', 'helper.py', 'halt_node', '&&',
                                      'python3', 'helper.py', 'restore', '--backup_path', './edge/malicious_rollback',
                                      '&&', 'python3', 'helper.py', 'start_validator', '--ip', node, '1>/dev/null', '2>/dev/null'])
        TestPatches.cb_wrapper.deposit("http://192.168.1.120:8545", TestPatches.alice.key.hex(), 1000000,
                                       ContractTypes.ERC20, TestPatches.n1.toWei(
                                           1, 'ether'), 100,
                                       TestPatches.contracts_n1[1], TestPatches.alice.address, RES_ID)
        response = relayer_client.ask_remap(
            "http://192.168.1.110:23456", "http://192.168.1.120:8545",
            TestPatches.n1.eth.get_block("latest")['number']-50, TestPatches.contracts_n1[1], RES_ID)
        self.assertEqual(response["response"], "NOK")

    # A relayer asks for remap. Smart contract code is not equal. Should fail.
    def test_07askRemapWrongCode(self):
        # We intentionally break the origin bridge
        proposal_id = TestPatches.governance_n1.remap_proposal([TestPatches.contracts_n1[0], RES_ID,
                                                                TestPatches.contracts_n1[0]],
                                                               "This seems to be a good idea.")
        TestPatches.governance_n1.vote_proposal(proposal_id, Vote.FOR)
        TestPatches.governance_n1.set_account(TestPatches.trudy)
        TestPatches.governance_n1.vote_proposal(proposal_id, Vote.FOR)
        time.sleep(WAIT)
        TestPatches.governance_n1.set_account(TestPatches.alice)
        receipt = TestPatches.governance_n1.execute_proposal(proposal_id)
        history = "resources/contract_storage_tries/45.json"
        if os.path.exists(history):
            os.remove(history)
        response = relayer_client.ask_remap(
            "http://192.168.1.110:23456", "http://192.168.1.120:8545",
            TestPatches.n1.eth.get_block("latest")['number']-50, TestPatches.contracts_n1[1], RES_ID)
        self.assertEqual(response["response"], "NOK")
        # Restore bridge
        proposal_id = TestPatches.governance_n1.remap_proposal([TestPatches.contracts_n1[2], RES_ID,
                                                                TestPatches.contracts_n1[0]],
                                                               "This is a good mapping.")
        TestPatches.governance_n1.vote_proposal(proposal_id, Vote.FOR)
        TestPatches.governance_n1.set_account(TestPatches.trudy)
        TestPatches.governance_n1.vote_proposal(proposal_id, Vote.FOR)
        time.sleep(WAIT)
        TestPatches.governance_n1.set_account(TestPatches.alice)
        receipt = TestPatches.governance_n1.execute_proposal(proposal_id)

    # Admin tries to refund an user sending wrong data to the smart contract. Should fail.
    def test_08refundWrongData(self):
        handler_addr = TestPatches.n1.toBytes(
            hexstr=TestPatches.contracts_n1[2]).rjust(32, b'\0')
        user_addr = TestPatches.n1.toBytes(
            hexstr=TestPatches.alice.address).rjust(32, b'\0')
        amount = TestPatches.n1.toBytes(
            TestPatches.n1.toWei(2, 'ether')).rjust(32, b'\0')
        data = handler_addr + user_addr + amount
        proposal_id = TestPatches.governance_n1.refund_user_proposal(
            TestPatches.contracts_n1[2], data, "Let's give him back his money!")
        TestPatches.governance_n1.vote_proposal(proposal_id, Vote.FOR)
        TestPatches.governance_n1.set_account(TestPatches.trudy)
        TestPatches.governance_n1.vote_proposal(proposal_id, Vote.FOR)
        time.sleep(WAIT)
        TestPatches.governance_n1.set_account(TestPatches.alice)
        receipt = TestPatches.governance_n1.execute_proposal(proposal_id)
        self.assertEqual(receipt['status'], 0)

    # Admin tries to refund an user sending good data to the smart contract.

    def test_09refundGoodData(self):
        handler_addr = TestPatches.n1.toBytes(
            hexstr=TestPatches.contracts_n1[2]).rjust(32, b'\0')
        user_addr = TestPatches.n1.toBytes(
            hexstr=TestPatches.alice.address).rjust(32, b'\0')
        amount = TestPatches.n1.toBytes(
            TestPatches.n1.toWei(1, 'ether')).rjust(32, b'\0')
        data = handler_addr + user_addr + amount
        proposal_id = TestPatches.governance_n1.refund_user_proposal(100, 1,
                                                                     TestPatches.contracts_n1[2], data, "Sorry, I made a mistake!")
        TestPatches.governance_n1.vote_proposal(proposal_id, Vote.FOR)
        TestPatches.governance_n1.set_account(TestPatches.trudy)
        TestPatches.governance_n1.vote_proposal(proposal_id, Vote.FOR)
        time.sleep(WAIT)
        TestPatches.governance_n1.set_account(TestPatches.alice)
        receipt = TestPatches.governance_n1.execute_proposal(proposal_id)
        self.assertEqual(receipt['status'], 1)

    # Admin withdraws the fee to early. Should fail.
    def test_10withdrawFeeTooEarly(self):
        pass

    # Admin whithdraw the fee after waiting enough time.
    def test_11withdrawFee(self):
        pass


if __name__ == "__main__":
    unittest.main()