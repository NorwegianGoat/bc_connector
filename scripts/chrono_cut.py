import logging
from utils.ufw_mod import UFW, REJECT, ALLOW
from utils.conntrack_mod import ConnTrack
from model.node import Node
from urllib.parse import urlparse
from utils.cb_wrapper import CBContracts, CBWrapper
from model.bc_resources import *
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


def deploy_bridge():
    # Deploy new bridge on source chain and save it on db
    out = cb.deploy(n0.get_endpoint(), acc.key.hex()[2:], 10000000, [
        CBContracts.BRIDGE, CBContracts.ERC20_HANDLER], [acc.address], 1, n0.chain_id)
    save_contracts(out.stdout, n0.chain_id)
    # Deploy new bridge on dest chain and save it on db
    out = cb.deploy(n1.get_endpoint(), acc.key.hex()[2:], 10000000, [
        CBContracts.BRIDGE, CBContracts.ERC20_HANDLER, CBContracts.ERC20], [acc.address], 1, n1.chain_id)
    save_contracts(out.stdout, n1.chain_id)
    print("Now you should update your config.json file on chainbridge")
    # Register resource on source and dest chains using the addresses of deployed bridges
    # TODO: save resource id on db
    # resource_id = '0x'+os.getrandom(32).hex()
    contracts = available_contracts(n0.chain_id)
    logging.info(contracts)
    cb.register_resource(n0.get_endpoint(), acc.key.hex()[
        2:], 10000000, contracts['bridge'], contracts['erc20Handler'], RESOURCE_ID_ERC20, contracts['erc20'])
    contracts = available_contracts(n1.chain_id)
    logging.info(contracts)
    cb.register_resource(n1.get_endpoint(), acc.key.hex()[
        2:], 10000000, contracts['bridge'], contracts['erc20Handler'], RESOURCE_ID_ERC20, contracts['erc20'])


def simple_erc20_transfer(amount: int):
    logging.info("Transferring " + str(amount) + " erc20 tokens")
    # Redeem tokens for this test
    redeem_tokens(n0.provider, acc, n0.provider.toWei(10, 'ether'))
    # Approves the erc20 handler to manage the amount of tokens
    contracts = available_contracts(n0.chain_id)
    cb.approve20(n0.get_endpoint(), acc.key.hex()[2:],
                 100000, n0.provider.toWei(10, 'ether'), contracts['erc20'], contracts['erc20Handler'])
    cb.deposit20(n0.get_endpoint(), acc.key.hex()[2:], 100000, n0.provider.toWei(10, 'ether'), 45,
                 contracts['bridge'], acc.address, RESOURCE_ID_ERC20)


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
    deploy_bridge()
    simple_erc20_transfer(10)
    # erc20_transfer_conn_lock()
    # ufw.ufw_disable()


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
    logging.info("Starting tests.")
    tests()
