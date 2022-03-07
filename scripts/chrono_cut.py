import logging
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
WAIT = 30
PKEY_PATH = 'crosscoin/.secret'


def block_connection(ip: str):
    ufw.alter_config(REJECT, ip)
    ct.drop(ip)


def unblock_connection(ip: str):
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
    # TODO: add option to update existing bridges
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


def simple_token_transfer(amount: int, type: ContractTypes):
    logging.info("Transferring " + str(amount) + " tokens")
    # Redeem tokens for this test
    redeem_tokens(n0.provider, acc, n0.provider.toWei(amount, 'ether'), type)
    # Gets the contract addresses for this type of transfer and the associated resource id
    contracts = available_contracts(n0.chain_id, type)
    res_id = available_resources(n0.chain_id, contracts['target'].id)
    if type == ContractTypes.ERC721:
        # For each nft fires an approve and transfer
        for i in range(amount):
            id = token_of_owner_by_index(n0.provider, acc.address, 0)
            cb.approve(n0.node_endpoint, acc.key.hex(), 100000, type, id,
                       contracts['target'].address, contracts['handler'].address)
            cb.deposit(n0.node_endpoint, acc.key.hex(), 100000, type, id,
                       45, contracts['bridge'].address, acc.address, res_id)
    elif type == ContractTypes.ERC20:
        # For erc20 we need just one request
        cb.approve(n0.node_endpoint, acc.key.hex(), 100000, type, amount,
                   contracts['target'].address, contracts['handler'].address)
        cb.deposit(n0.node_endpoint, acc.key.hex(), 100000, type, amount,
                   45, contracts['bridge'].address, acc.address, res_id)


def transfer_conn_lock():
    logging.info("Erc20 transfer with connection lock.")
    ip1 = urlparse(n1.node_endpoint).hostname
    # Connection to dest chain is blocked
    block_connection(ip1)
    # Basic erc20 transfer is fired, but destination is currently unreachable
    simple_token_transfer(1, ContractTypes.ERC20)
    time.sleep(60)
    logging.info("Waiting")
    # We block source chain and then unblock destination
    ip0 = urlparse(n0.node_endpoint).hostname
    block_connection(ip0)
    unblock_connection(ip1)


def tests():
    # deploy_bridge(ContractTypes.ERC20)
    # simple_token_transfer(1, ContractTypes.ERC20)
    transfer_conn_lock()
    #ufw.ufw_disable()


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
