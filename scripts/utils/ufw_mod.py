import ipaddress
import subprocess
import argparse
import logging
from utils.sys_mod import check_package

DENY = "deny"
REJECT = "reject"
ALLOW = "allow"


class UFW():
    def __init__(self):
        self.is_installed = check_package("ufw")
        if self.is_installed:
            self.ufw_enable()
        else:
            exit("ufw seems not to be installed, can't do anything.")

    def ufw_enable(self):
        subprocess.run(["sudo", "ufw", "enable"])

    def ufw_disable(self):
        subprocess.run(["sudo", "ufw", "disable"])

    def alter_config(self, action: str, ip: str):
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            exit(ip + " is not an ip address.")
        logging.info(action + " " + ip)
        if action == DENY:
            subprocess.run(["sudo", "ufw", DENY, 'out', 'to', ip])
        elif action == REJECT:
            subprocess.run(["sudo", "ufw", REJECT, 'out', 'to', ip])
        elif action == ALLOW:
            subprocess.run(["sudo", "ufw", ALLOW, 'out', 'to', ip])
        else:
            exit("Action " + action + "not implemented.")

if __name__ == "__main__":
    # Logging setup
    logging.basicConfig(level=logging.INFO)
    # cli parser
    parser = argparse.ArgumentParser(
        description="Utility for bridge cutting simulation. It blocks in/out connections using ufw rules")
    actions = parser.add_subparsers(dest='command')
    # Unblock ip command
    unblock = actions.add_parser("unblock")
    unblock.add_argument("--ip", type=str, required=True)
    # Block ip command
    block = actions.add_parser("block")
    block.add_argument("--ip", type=str, required=True)
    # Retrive arge
    args = parser.parse_args()
    # Fire action
    ufw = UFW()
    ufw.alter_config(args.command, args.ip)
