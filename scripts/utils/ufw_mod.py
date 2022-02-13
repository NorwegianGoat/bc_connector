import ipaddress
import subprocess
import argparse
import logging

BLOCK = "block"
UNBLOCK = "unblock"


class UFW():
    def __init__(self):
        self.is_present = UFW._ufw_check()
        if self.is_present:
            self.ufw_enable()

    def _ufw_check() -> bool:
        is_present = subprocess.run(
            ["dpkg", "-s", "ufw"], stdout=subprocess.DEVNULL)
        # is_present = 0 if ufw is present, is_present = 1 if ufw is not
        # installed so we need to "invert" the process exit code
        is_present = not is_present.returncode
        return is_present

    def ufw_enable(self):
        subprocess.run(["sudo", "ufw", "enable"])

    def ufw_disable(self):
        subprocess.run(["sudo", "ufw", "disable"])

    def alter_config(self, action: str, ip: str):
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            exit(ip + " is not an ip address.")
        if self.is_present:
            logging.info(action + " " + ip)
            if action == BLOCK:
                subprocess.run(["sudo", "ufw", 'deny', 'out', 'to', ip])
            elif action == UNBLOCK:
                subprocess.run(["sudo", "ufw", 'allow', 'out', 'to', ip])
        else:
            exit("ufw seems not to be installed, can't do anything.")


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
