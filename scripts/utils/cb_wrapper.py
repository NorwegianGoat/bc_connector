import subprocess
from typing import List
from utils.sys_mod import check_program
from utils.resource_manager import available_contracts
from enum import Enum
import logging
import os
import json

CONFIG_JSON_FILE = 'resources/config.json'


class CBContracts(str, Enum):
    BRIDGE = "bridge"
    ERC20_HANDLER = "erc20Handler"
    ERC20 = "erc20"
    ERC721_HANDLER = "erc721Handler"
    ERC721 = "erc721"
    GENERIC_HANDLER = "genericHandler"


class CBWrapper():
    '''This is a simple wrapper to call cb-sol-cli functions from
    python. For config and params info check the official documentation at
    https://github.com/ChainSafe/chainbridge-deploy/blob/main/cb-sol-cli/README.md#usage
    This wrapper is also used to manage chainbridge relay.'''

    def __init__(self):
        self.cb_sol_cli = check_program("cb-sol-cli")
        self.chainbridge = check_program("chainbridge")
        if not self.cb_sol_cli:
            exit("No cb-sol-cli. Please install cb-sol-cli.")
        if not self.chainbridge:
            print("Chainbridge relayer not installed")
        else:
            if self.is_chainbridge_running():
                logging.info("Bridge already running, it will not be started")
            else:
                self.start_relay()

    def _basic_config(self, gateway: str, pkey: str, gas: int):
        return ['cb-sol-cli', '--url', gateway, '--privateKey',
                pkey, '--gasPrice', str(gas)]

    def _run_command(self, params) -> subprocess.CompletedProcess:
        logging.info(params)
        out = subprocess.run(params, capture_output=True)
        print(out.stdout.decode("UTF-8"))
        return out

    def is_chainbridge_running(self):
        if self.chainbridge:
            params = ['pgrep', 'chainbridge']
            out = subprocess.run(params, capture_output=True)
            return not out.returncode
        else:
            return False

    def start_relay(self):
        params = ['nohup', 'chainbridge', '--config',
                  os.path.abspath(CONFIG_JSON_FILE), '--verbosity', 'trace', '--latest', '&']
        logging.info("Starting chainbridge relay")
        subprocess.Popen(params, cwd=os.path.realpath('..'))

    def stop_relay(self):
        logging.info("Stopping chainbridge relay")
        params = ['pgrep', 'chainbridge']
        pid = subprocess.run(
            params, capture_output=True).stdout.decode('UTF-8').strip()
        params = ['kill', '-15', pid]
        subprocess.run(params)

    def deploy(self, gateway: str, pkey: str, gas: int, contracts_to_deploy: List[CBContracts],
               relayer_addresses: List[str], relayer_threshold: int, chain_id: int):
        params = self._basic_config(gateway, pkey, gas)
        params.append('deploy')
        params += ["--"+contract for contract in contracts_to_deploy]
        if CBContracts.BRIDGE in contracts_to_deploy:
            params.append('--relayers')
            params += relayer_addresses
            params += ['--relayerThreshold',
                       str(relayer_threshold), "--chainId", str(chain_id)]
        return self._run_command(params)

    def register_resource(self, gateway: str, pkey: str, gas: int, bridge_addr: str,
                          handler_addr: str, resource_id: str, target_contract: str):
        params = self._basic_config(gateway, pkey, gas)
        params.insert(1, 'bridge')
        params.insert(2, 'register-resource')
        params += ['--bridge', bridge_addr, '--handler', handler_addr, '--resourceId', resource_id,
                   '--targetContract', target_contract]
        return self._run_command(params)

    def burnable(self, gateway: str, pkey: str, gas: int, bridge_addr: str,
                 handler_addr: str, target_contract: str):
        params = self._basic_config(gateway, pkey, gas)
        params.insert(1, 'bridge')
        params.insert(2, 'set-burn')
        params += ['--bridge', bridge_addr, '--handler',
                   handler_addr, '--tokenContract', target_contract]
        return self._run_command(params)

    def add_minter(self, gateway: str, pkey: str, gas: int, type: CBContracts, minter: str, target_contract: str):
        params = self._basic_config(gateway, pkey, gas)
        if type == CBContracts.ERC20:
            params.insert(1, 'erc20')
            params += ['--erc20Address', target_contract]
        elif type == CBContracts.ERC721:
            params.insert(1, '--erc721')
            params += ['--erc721Address', target_contract]
        params.insert(2, 'add-minter')
        params += ['--minter', minter]
        return self._run_command(params)

    def approve(self, gateway: str, pkey: str, gas: int, type: CBContracts, amount: int, target: str,
                recipient: str):
        params = self._basic_config(gateway, pkey, gas)
        if type == CBContracts.ERC20:
            params.insert(1, "erc20")
            params += ['--amount', amount, '--erc20Address', target]
        elif type == CBContracts.ERC721:
            params.insert(1, "erc721")
            params += ['--id', hex(amount), '--erc721Address', target]
        params.insert(2, 'approve')
        params += ['--recipient', recipient]
        return self._run_command(params)

    def deposit(self, gateway: str, pkey: str, gas: int, type: CBContracts, amount: int, dest: int,
                bridge: str, recipient: str, resource_id: str):
        params = self._basic_config(gateway, pkey, gas)
        if type == CBContracts.ERC20:
            params.insert(1, "erc20")
            params += ['--amount', amount]
        elif type == CBContracts.ERC721:
            params.insert(1, "erc721")
            params += ['--id', hex(amount)]
        params.insert(2, 'deposit')
        params += ['--dest', str(dest), '--bridge', bridge,
                   '--recipient', recipient, '--resourceId', resource_id]
        return self._run_command(params)

    def update_config_json(self, chain_id):
        with open(CONFIG_JSON_FILE, 'r+') as f:
            jsonfile = json.load(f)
            contracts = available_contracts(chain_id)
            # we search for the right chain config json object in the whole list
            for i in range(len(jsonfile['chains'])):
                if jsonfile['chains'][i]['id'] == str(chain_id):
                    # For each contract available in the chain we update the address on the json
                    # so it makes no difference if we used a erc20/721/generic handler contract
                    for key in contracts.keys():
                        if key == 'erc20' or key == 'erc721':
                            # The config file does not contain the erc20/721 endpoint
                            pass
                        else:
                            jsonfile['chains'][i]['opts'][key] = contracts[key].address
                    f.seek(0)
                    f.truncate()
                    json.dump(jsonfile, f, indent=4)
                    break
        self.stop_relay()
        self.start_relay()
