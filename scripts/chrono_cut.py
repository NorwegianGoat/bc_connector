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
    # Bridge creation
    #cb.deploy(n0.get_endpoint(), acc.key.hex()[2:], 10000000, [
    #    CBContracts.BRIDGE, CBContracts.ERC20_HANDLER], [acc.address], 1, 100)
    #cb.deploy(n1.get_endpoint(), acc.key.hex()[2:], 10000000, [
    #          CBContracts.BRIDGE, CBContracts.ERC20_HANDLER, CBContracts.ERC20], [acc.address], 1, 45)
    # print("Now you should update your bc_resources file and config.json file on chainbridge")
    # Register resource
    #resource_id = '0x'+os.getrandom(32).hex()
    #cb.register_resource(n0.get_endpoint(), acc.key.hex()[
    #    2:], 10000000, C0_BRIDGE_ADDRESS, C0_ERC20_HANDLER, RESOURCE_ID_ERC20, C0_ERC20)
    #cb.register_resource(n1.get_endpoint(), acc.key.hex()[
    #    2:], 10000000, C1_BRIDGE_ADDRESS, C1_ERC20_HANDLER, RESOURCE_ID_ERC20, C1_ERC20)
    pass

def simple_erc20_transfer(amount: int):
    logging.info("Transferring " + str(amount) + " erc20 tokens")
    redeem_tokens(n0.provider, acc, n0.provider.toWei(10, 'ether'))
    # Approves the erc20 handler to manage the amount of tokens
    #cb.approve20(n0.get_endpoint(), acc.key.hex()[2:],
    #             100000, n0.provider.toWei(10, 'ether'), C0_ERC20, C0_ERC20_HANDLER)
    #cb.deposit20(n0.get_endpoint(), acc.key.hex()[2:], 100000, n0.provider.toWei(10, 'ether'), 45,
    #             C0_BRIDGE_ADDRESS, acc.address, RESOURCE_ID_ERC20)


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
    # deploy_bridge()
    simple_erc20_transfer(10)
    # erc20_transfer_conn_lock()
    #ufw.ufw_disable()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Configuring nodes
    #n0 = Node(N0_C0_URL, 100)
    n0 = Node('http://127.0.0.1:8545', 100)
    n1 = Node(N0_C1_URL, 200)
    n2 = Node(N0_C2_URL, 300)
    # Configuring test accounts
    with open(PKEY_PATH) as f:
        key = f.readline().strip()
    acc = n0.provider.eth.account.from_key(key)
    logging.info("Imported account:" + acc.address)
    # Configuring wrappers for commands execution
    #cb = CBWrapper()
    #ufw = UFW()
    #ct = ConnTrack()
    logging.info("Starting tests.")
    tests()
