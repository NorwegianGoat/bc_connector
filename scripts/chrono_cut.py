import time
import logging
from utils.ufw_mod import UFW, REJECT, ALLOW
from utils.conntrack_mod import ConnTrack
from model.eth_account import EthAcc
from model.node import Node
from urllib.parse import urlparse

# Endpoints
N0_C0_URL = "http://192.168.1.110:8545"
N0_C1_URL = "http://192.168.1.120:8545"
N0_C2_URL = "http://192.168.1.130:8545"
WAIT = 1


def _alter_connections():
    ip = urlparse(n0.get_endpoint()).hostname
    for i in range(0, 10):
        ufw.alter_config(REJECT, ip)
        ct.drop(ip)
        time.sleep(WAIT)
        ufw.alter_config(ALLOW, ip)
        time.sleep(WAIT)
    ufw.ufw_disable()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Configuring nodes
    n0 = Node(N0_C0_URL, 100)
    n1 = Node(N0_C1_URL, 300)
    n2 = Node(N0_C2_URL, 300)
    # Configuring test accounts
    acc = EthAcc(
        "1cc24d8d38497d3257350b106e50f8093d1285cc691f45dd6e68ee601756ce43")
    logging.info("Starting chrono ufw alter script.")
    ufw = UFW()
    ct = ConnTrack()
    _alter_connections()
