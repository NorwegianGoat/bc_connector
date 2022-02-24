import subprocess
from typing import List
from utils.sys_mod import check_program
from enum import Enum
import logging


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
    https://github.com/ChainSafe/chainbridge-deploy/blob/main/cb-sol-cli/README.md#usage'''

    def __init__(self):
        self.is_installed = check_program("cb-sol-cli")
        if not self.is_installed:
            exit("No cb-sol-cli. Please install cb-sol-cli.")

    def _basic_config(self, gateway: str, pkey: str, gas: int):
        return ['cb-sol-cli', '--url', gateway, '--privateKey',
                pkey, '--gasPrice', str(gas)]

    def deploy(self, gateway: str, pkey: str, gas: int, contracts_to_deploy: List[CBContracts],
               relayer_addresses: List[str], relayer_threshold: int, chain_id: int):
        params = self._basic_config(gateway, pkey, gas)
        params.append('deploy')
        params += ["--"+contract for contract in contracts_to_deploy]
        if CBContracts.BRIDGE in contracts_to_deploy:
            params.append('--relayers')
            params += relayer_addresses
            params += ['--relayerThreshold',
                       str(relayer_threshold), " --chainId ", str(chain_id)]
        subprocess.call(params)

    def register_resource(self, gateway: str, pkey: str, gas: int, bridge_addr: str,
                          handler_addr: str, resource_id: str, target_contract: str):
        params = self._basic_config(gateway, pkey, gas)
        params.insert(1, 'bridge')
        params.insert(2, 'register-resource')
        params += ['--bridge', bridge_addr, '--handler', handler_addr, '--resourceId', resource_id,
                   '--targetContract', target_contract]
        subprocess.call(params)

    def approve20(self, gateway: str, pkey: str, gas: int, amount: int, erc20_addr: str,
                  recipient: str):
        params = self._basic_config(gateway, pkey, gas)
        params.insert(1, "erc20")
        params.insert(2, 'approve')
        params += ['--amount', str(amount), '--erc20Address', erc20_addr,
                   '--recipient', recipient]
        subprocess.call(params)

    def deposit20(self, gateway: str, pkey: str, gas: int, amount: int, dest: int,
                  bridge: str, recipient: str, resource_id: str):
        params = self._basic_config(gateway, pkey, gas)
        params.insert(1, "erc20")
        params.insert(2, 'deposit')
        params += ['--amount', str(amount), '--dest', str(dest),
                   '--bridge', bridge, '--recipient', recipient, '--resourceId', resource_id]
        subprocess.call(params)

    def approve721(self, gateway: str, pkey: str, gas: int, token_id: int, erc721_addr: str,
                   recipient: str):
        '''gateway: The node managing the request
        pkey: the private key of the user that is giving the recipient the autorization to manage his tokens
        gas: the gas for the computation
        token_id: the NFT id we are autorizing the bridge to manage to
        erc721_addr: the addrress of the smart contract related to the nft
        recipient: the address we are autorizing to manage our asset (the erc721 handler contract)
        '''
        params = self._basic_config(gateway, pkey, gas)
        params.insert(1, "erc721")
        params.insert(2, 'approve')
        params += ['--id', str(hex(token_id)), '--erc721Address', erc721_addr,
                   '--recipient', recipient]
        subprocess.call(params)

    def deposit721(self, gateway: str, pkey: str, gas: int, token_id: int, dest: int,
                   bridge: str, recipient: str, resource_id: str):
        '''dest: chain id of token destination.'''
        params = self._basic_config(gateway, pkey, gas)
        params.insert(1, "erc721")
        params.insert(2, 'deposit')
        params += ['--id', str(hex(token_id)), '--dest', str(dest),
                   '--bridge', bridge, '--recipient', recipient, '--resourceId', resource_id]
        subprocess.call(params)
