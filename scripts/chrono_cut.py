import time
import logging
from utils.ufw_mod import UFW, REJECT, ALLOW
from utils.conntrack_mod import ConnTrack
from model.eth_account import EthAcc
from model.node import Node
from urllib.parse import urlparse
from utils.cb_wrapper import CBWrapper

# Endpoints
N0_C0_URL = "http://192.168.1.110:8545"
N0_C1_URL = "http://192.168.1.120:8545"
N0_C2_URL = "http://192.168.1.130:8545"
WAIT = 30
# Blockchain addresses and data
SOURCE_NFT_ADDR = '0xC671538D5A6BccAe6cB931008fFC45F9328290fd'
SOURCE_NFT_HANDLER = '0xAA0ED9D26180Ea1B80731F2A6f65c2eAA1809251'
SOURCE_BRIDGE_ADDR = '0x8c93A7aab57B43fA0fFa0C5b69500C70e7e58CA7'
RESOURCE_ID = '0x000000000000000000000000000000c76ebe4a02bbc34786d860b355f5a5ce00'# Binds the tokens between the two chains
# Pkey path
PKEY_PATH = 'crosscoin/.secret'


def block_connection(ip: str):
    ufw.alter_config(REJECT, ip)
    ct.drop(ip)


def unblock_connection(ip: str):
    ufw.alter_config(ALLOW, ip)


def simple_erc721_transfer():
    logging.info("Simple erc721 transfer started.")
    cb.approve721(n0.get_endpoint(), acc.get_pkey(), 1000000, 100,
                  SOURCE_NFT_ADDR, SOURCE_NFT_HANDLER)
    cb.deposit721(n0.get_endpoint(), acc.get_pkey(), 1000000, 100,
                  101, SOURCE_BRIDGE_ADDR, acc.get_address(), RESOURCE_ID)


def tests():
    simple_erc721_transfer()
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
    # Configuring wrappers
    cb = CBWrapper()
    ufw = UFW()
    ct = ConnTrack()
    logging.info("Starting tests.")
    tests()
