import subprocess
from typing import List
from web3 import HTTPProvider, Web3
from utils.sys_mod import check_program
from utils.resource_manager import available_contracts
from utils.contracts_utils import load_abi
from model.contract import ContractTypes
from model.node import Node
import logging
import os
import json

CONFIG_JSON_FILE = 'resources/config.json'


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
            if self.is_relayer_running():
                logging.info("Bridge already running, it will not be started")

    def _basic_config(self, gateway: str, pkey: str, gas: int):
        return ['cb-sol-cli', '--url', gateway, '--privateKey',
                pkey, '--gasPrice', str(gas)]

    def _run_command(self, params) -> subprocess.CompletedProcess:
        logging.info(params)
        out = subprocess.run(params, capture_output=True)
        print(out.stdout.decode("UTF-8"))
        return out

    def is_relayer_running(self):
        if self.chainbridge:
            params = ['pgrep', 'chainbridge']
            out = subprocess.run(params, capture_output=True)
            return not out.returncode
        else:
            return False

    def start_relay(self, latest: bool = False, start_block: int = None):
        if latest and start_block:
            raise ValueError(
                "You can't specify both latest and from_block params.")
        params = ['nohup', 'chainbridge', '--config',
                  os.path.abspath(CONFIG_JSON_FILE), '--verbosity', 'trace', '&']
        if latest:
            params.append("--latest")
        if start_block:
            params.append("--startBlock")
            params.append(start_block)
        logging.info("Starting chainbridge relay")
        subprocess.Popen(params, cwd=os.path.realpath('..'))

    def stop_relay(self):
        logging.info("Stopping chainbridge relay")
        params = ['pgrep', 'chainbridge']
        relay = subprocess.Popen(params, stdout=subprocess.PIPE)
        subprocess.run(['xargs', '-I{}', 'kill', "{}"], stdin=relay.stdout)

    def deploy(self, gateway: str, pkey: str, gas: int, contracts_to_deploy: List[ContractTypes],
               relayer_addresses: List[str], relayer_threshold: int, chain_id: int):
        params = self._basic_config(gateway, pkey, gas)
        params.append('deploy')
        for contract in contracts_to_deploy:
            # If the list contains an address it is used as bridge address
            if "0x" in contract:
                params += ['--bridgeAddress', contract]
            else:
                params += ["--"+contract]
        if ContractTypes.BRIDGE in contracts_to_deploy:
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

    def add_minter(self, gateway: str, pkey: str, gas: int, type: ContractTypes, minter: str, target_contract: str):
        params = self._basic_config(gateway, pkey, gas)
        if type == ContractTypes.ERC20:
            params.insert(1, 'erc20')
            params += ['--erc20Address', target_contract]
        elif type == ContractTypes.ERC721:
            params.insert(1, '--erc721')
            params += ['--erc721Address', target_contract]
        params.insert(2, 'add-minter')
        params += ['--minter', minter]
        return self._run_command(params)

    def approve(self, gateway: str, pkey: str, gas: int, type: ContractTypes, amount: int, target: str,
                recipient: str):
        params = self._basic_config(gateway, pkey, gas)
        if type == ContractTypes.ERC20:
            params.insert(1, "erc20")
            params += ['--amount', str(amount), '--erc20Address', target]
        elif type == ContractTypes.ERC721:
            params.insert(1, "erc721")
            params += ['--id', hex(amount), '--erc721Address', target]
        params.insert(2, 'approve')
        params += ['--recipient', recipient]
        return self._run_command(params)

    # This is used for the patched version of the bridge
    def manual_deposit(self, gateway: str, chain_id: int, pkey: str, gas: int, amount: int,
                       bridge: str, token_addr: str, resource_id: str):
        w3 = Web3(HTTPProvider(gateway))
        account = w3.eth.account.from_key(pkey)
        abi = load_abi("crosscoin/build/contracts/BridgeWithdrawPatch.json")
        contract = w3.eth.contract(address=bridge, abi=abi)
        # Fire deposit transaction
        token_addr = w3.toBytes(
            hexstr=token_addr).rjust(32, b'\0')
        user_addr = w3.toBytes(
            hexstr=account.address).rjust(32, b'\0')
        amount = w3.toBytes(
            w3.toWei(1, "ether")).rjust(32, b'\0')
        data = token_addr + user_addr + amount
        fee_data = w3.toBytes(0).rjust(32, b'\0')
        t_dict = {"chainId": w3.eth.chain_id,
                  "nonce": w3.eth.get_transaction_count(account.address, 'pending'),
                  "gasPrice": w3.toWei(10,"gwei"),
                  "gas": gas}
        tx = contract.functions.deposit(
            chain_id, w3.toBytes(hexstr=resource_id), data, fee_data).buildTransaction(t_dict)
        signed_tx = w3.eth.account.sign_transaction(tx, account.key)
        tx_hash = w3.eth.send_raw_transaction(
            signed_tx.rawTransaction)
        logging.info(account.address + ' is depositing ' + str(data) + ' on chain ' + str(
            t_dict['chainId']) + " tx_hash " + tx_hash.hex())
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print("root update tx_receipt: " + str(receipt))

    def deposit(self, gateway: str, pkey: str, gas: int, type: ContractTypes, amount: int, dest: int,
                bridge: str, recipient: str, resource_id: str):
        params = self._basic_config(gateway, pkey, gas)
        if type == ContractTypes.ERC20:
            params.insert(1, "erc20")
            params += ['--amount', str(amount)]
        elif type == ContractTypes.ERC721:
            params.insert(1, "erc721")
            params += ['--id', hex(amount)]
        params.insert(2, 'deposit')
        params += ['--dest', str(dest), '--bridge', bridge,
                   '--recipient', recipient, '--resourceId', resource_id]
        return self._run_command(params)

    def balance(self, gateway: str, type: ContractTypes, address: str, resource: str):
        params = ['cb-sol-cli']
        if type == ContractTypes.ERC20:
            params += ['erc20', 'balance', '--address',
                       address, '--erc20Address', resource]
        elif type == ContractTypes.ERC721:
            params += ['erc721', 'owner', '--erc721Address',
                       address, '--id', resource]
        params += ['--url', gateway]
        self._run_command(params)

    def update_config_json(self, endpoint: Node, type):
        logging.info("Updating chainbridge conf.")
        if self.is_relayer_running():
            self.stop_relay()
        chain_id = endpoint.chain_id
        with open(CONFIG_JSON_FILE, 'r+') as f:
            jsonfile = json.load(f)
            contracts = available_contracts(chain_id, type)
            has_chain = False
            # we search for the right chain config json object in the whole list
            for i in range(len(jsonfile['chains'])):
                if jsonfile['chains'][i]['id'] == str(chain_id):
                    has_chain = True
                    # Node endpoint may be changed!
                    jsonfile['chains'][i]['endpoint'] = endpoint.node_endpoint
                    # For each contract available in the chain we update the address on the json
                    # so it makes no difference if we used a erc20/721/generic handler contract
                    for contract in contracts.values():
                        if contract.type == 'erc20' or contract.type == 'erc721':
                            # The config file does not contain the erc20/721 endpoint
                            # so we skip them
                            pass
                        else:
                            jsonfile['chains'][i]['opts'][contract.type] = contract.address
            if not has_chain:
                # We configure the second chain item as a new chain
                jsonfile['chains'][1]['id'] = str(chain_id)
                jsonfile['chains'][1]['endpoint'] = endpoint.node_endpoint
                for contract in contracts.values():
                    if contract.type == 'erc20' or contract.type == 'erc721':
                        # The config file does not contain the erc20/721 endpoint
                        # so we skip them
                        pass
                    else:
                        jsonfile['chains'][1]['opts'][contract.type] = contract.address
            f.seek(0)
            f.truncate()
            json.dump(jsonfile, f, indent=4)
        self.start_relay()
