import ipaddress
import subprocess
import argparse
import logging
from utils.sys_mod import check_package
import os

DENY = "deny"
REJECT = "reject"
ALLOW = "allow"
UFW_RULES_DEF_PATH = '/etc/ufw/user.rules'
UFW_RULES_LOCAL_BACKUP = os.path.join(
    os.path.realpath('.'), 'resources/user.rules')


class UFW():
    def __init__(self):
        self.is_installed = check_package("ufw")
        if self.is_installed:
            self.ufw_backup_rules()
        else:
            exit("ufw seems not to be installed, can't do anything.")

    def ufw_backup_rules(self):
        subprocess.run(
            ['sudo', 'cp', UFW_RULES_DEF_PATH, UFW_RULES_LOCAL_BACKUP])

    def ufw_restore_rules(self):
        subprocess.run(
            ['sudo', 'mv', UFW_RULES_LOCAL_BACKUP, UFW_RULES_DEF_PATH, ])

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
