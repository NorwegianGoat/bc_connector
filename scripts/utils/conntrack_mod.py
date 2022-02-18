import ipaddress
import subprocess
import argparse
import logging
from utils.sys_mod import check_package


class ConnTrack():
    def __init__(self):
        self.is_installed = check_package("conntrack")
        if not self.is_installed:
            exit('conntrack not found')

    def drop(self, ip: str):
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            exit(ip + " is not an ip address.")
        logging.info("Dopping existing connection to " + ip)
        subprocess.run(["sudo", "conntrack", "-D", "-d", ip])


if __name__ == "__main__":
    # Logging setup
    logging.basicConfig(level=logging.INFO)
    # cli parser
    parser = argparse.ArgumentParser(
        description="Utility for managing connections using conntrack.")
    actions = parser.add_subparsers(dest='command')
    # drop connection
    drop = actions.add_parser("drop")
    drop.add_argument("--ip", type=str, required=True)
    args = parser.parse_args()
    # Fire action
    ct = ConnTrack()
    ct.drop(args.ip)
