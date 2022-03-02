import logging
from typing import List
from utils.ufw_mod import UFW, REJECT, ALLOW
from utils.conntrack_mod import ConnTrack
from model.node import Node
from urllib.parse import urlparse
from utils.cb_wrapper import CBContracts, CBWrapper
from utils.resource_manager import *
from utils.cc_redeem import redeem_tokens
import random
import os

# Endpoints
N0_C0_URL = "http://192.168.1.110:8545"
N0_C1_URL = "http://192.168.1.120:8545"
N0_C2_URL = "http://192.168.1.130:8545"
WAIT = 30
PKEY_PATH = 'crosscoin/.secret'


def block_connection(ip: str):
    ufw.alter_config(REJECT, ip)
    ct.drop(ip)


def unblock_connection(ip: str):
    ufw.alter_config(ALLOW, ip)


def simple_erc721_transfer():
    logging.info("Simple erc721 transfer started.")
    cb.approve721(n0.get_endpoint(), acc.get_pkey(), 1000000, 1,
                  C0_NFT, C0_NFT_HANDLER)
    cb.deposit721(n0.get_endpoint(), acc.get_pkey(), 1000000, 1,
                  45, C0_BRIDGE_ADDRESS, acc.get_address(), RESOURCE_ID_NFT)


def _deploy_bridge(endpoint: Node, contracts: List[CBContracts]):
    # Deploy new bridge on chain and save it on db
    out = cb.deploy(endpoint.get_endpoint(), acc.key.hex(),
                    10000000, contracts, [acc.address], 1, endpoint.chain_id)
    save_contracts(out.stdout, endpoint.chain_id)


def _register_resource(endpoint: Node, resource_id: str, type: CBContracts):
    # Registers resource on chain and save on local db
    dest_chain_config = True
    if not resource_id:
        resource_id = '0x'+os.getrandom(32).hex()
        dest_chain_config = False
    contracts = available_contracts(endpoint.chain_id)
    logging.info(contracts)
    resources = {"bridge": contracts['bridge']}
    if type == CBContracts.ERC20:
        resources['handler'] = contracts['erc20Handler']
        resources['target'] = contracts['erc20']
    elif type == CBContracts.ERC721:
        resources['handler'] = contracts['erc721Handler']
        resources['target'] = contracts['erc721']
    cb.register_resource(endpoint.get_endpoint(), acc.key.hex(
    ), 10000000, resources['bridge'].address, resources['handler'].address, resource_id, resources['target'].address)
    save_binding(resource_id, resources['bridge'].id,
                 resources['handler'].id, resources['target'].id, endpoint.chain_id)
    if dest_chain_config:
        # If this is a first deploy we are on a destination chain so we need to
        # set up the new token as burnable and add the minter
        cb.burnable(endpoint.get_endpoint(), acc.key.hex(), 10000000,
                    resources['bridge'].address, resources['handler'].address, resources['target'].address)
        cb.add_minter(endpoint.get_endpoint(), acc.key.hex(),
                      10000000, type, resources['handler'].address, resources['target'].address)
    return resource_id


def deploy_bridge(type: CBContracts):
    contracts_source = []
    contracts_dest = []
    if type == CBContracts.ERC20:
        contracts_source += [CBContracts.BRIDGE, CBContracts.ERC20_HANDLER]
        contracts_dest += [CBContracts.BRIDGE,
                           CBContracts.ERC20_HANDLER, CBContracts.ERC20]
    elif type == CBContracts.ERC721:
        contracts_source += [CBContracts.BRIDGE, CBContracts.ERC721_HANDLER]
        contracts_dest += [CBContracts.BRIDGE,
                           CBContracts.ERC721_HANDLER, CBContracts.ERC721]
    _deploy_bridge(n0, contracts_source)
    _deploy_bridge(n1, contracts_dest)
    # The vulnerability in the whole process is the fact that the user is the ralayer
    res_id_origin = _register_resource(n0, None, type)
    _register_resource(n1, res_id_origin, type)
    cb.update_config_json(n0.chain_id)
    cb.update_config_json(n1.chain_id)


def simple_erc20_transfer(amount: int):
    logging.info("Transferring " + str(amount) + " tokens")
    # Redeem tokens for this test
    redeem_tokens(n0.provider, acc, n0.provider.toWei(10, 'ether'))
    # Approves the erc20 handler to manage the amount of tokens
    contracts = available_contracts(n0.chain_id)
    cb.approve20(n0.get_endpoint(), acc.key.hex(), 100000, n0.provider.toWei(
        10, 'ether'), contracts['erc20'].address, contracts['erc20Handler'].address)
    res_id = available_resources(n0.chain_id, contracts['erc20'].id)
    cb.deposit20(n0.get_endpoint(), acc.key.hex(), 100000, n0.provider.toWei(
        10, 'ether'), 45, contracts['bridge'].address, acc.address, res_id)


def erc20_transfer_conn_lock():
    logging.info("Erc20 transfer with connection lock.")
    ip1 = urlparse(n1.get_endpoint()).hostname
    # Connection to dest chain is blocked
    block_connection(ip1)
    # Basic erc20 transfer is fired, but destination is currently unreachable
    simple_erc20_transfer()
    # We block source chain and then unblock destination
    ip0 = urlparse(n0.get_endpoint()).hostname
    block_connection(ip0)
    unblock_connection(ip1)


def tests():
    # simple_erc721_transfer()
    deploy_bridge(CBContracts.ERC721)
    # simple_erc20_transfer(10)
    # erc20_transfer_conn_lock()
    # ufw.ufw_disable()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Configuring nodes
    n0 = Node(N0_C0_URL)
    n1 = Node(N0_C1_URL)
    n2 = Node(N0_C2_URL)
    # Configuring test accounts
    with open(PKEY_PATH) as f:
        key = f.readline().strip()
    acc = n0.provider.eth.account.from_key(key)
    logging.info("Imported account:" + acc.address)
    # Configuring wrappers for commands execution
    cb = CBWrapper()
    ufw = UFW()
    ct = ConnTrack()
    logging.info("Starting tests.")
    tests()
