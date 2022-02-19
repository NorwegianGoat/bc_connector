import time
import logging
from utils.ufw_mod import UFW, REJECT, ALLOW
from utils.conntrack_mod import ConnTrack
from model.eth_account import EthAcc
from model.node import Node
from urllib.parse import urlparse
from utils.cb_wrapper import CBWrapper
from model.bc_resources import C0_NFT_HANDLER, C0_NFT, C0_BRIDGE_ADDRESS, C0_ERC20, RESOURCE_ID_NFT

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
                  101, C0_BRIDGE_ADDRESS, acc.get_address(), RESOURCE_ID_NFT)


def simple_erc20_transfer():
    logging.info("Simple erc20 transfer started.")


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
    simple_erc20_transfer()
    # erc20_transfer_conn_lock()
    ufw.ufw_disable()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Configuring nodes
    n0 = Node(N0_C0_URL, 100)
    n1 = Node(N0_C1_URL, 200)
    n2 = Node(N0_C2_URL, 300)
    # Configuring test accounts
    with open(PKEY_PATH) as f:
        key = f.readline().strip()
    acc = EthAcc(key)
    # Configuring wrappers for commands execution
    cb = CBWrapper()
    ufw = UFW()
    ct = ConnTrack()
    logging.info("Starting tests.")
    tests()
