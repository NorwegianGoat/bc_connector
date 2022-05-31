import subprocess
from utils.sys_mod import check_program
import os

COMMAND = "truffle"


class Truffle():
    def __init__(self, endpoint: str):
        if check_program(COMMAND):
            self.endpoint = endpoint
        else:
            exit("Truffle seems not to be installed.")

    def run_migration(self, f: int, t: int):
        os.chdir("crosscoin")
        command = [COMMAND, 'migrate',
                   '--network', self.endpoint, '-f', str(f), '-t', str(t)]
        out = subprocess.run(command, capture_output=True, text=True)
        addresses = []
        for line in out.stdout.splitlines(keepends=True):
            intestation = '> contract address:'
            if intestation in line:
                addresses.append(line.replace(intestation, "").strip())
        os.chdir('..')
        return addresses
