from web3 import HTTPProvider, Web3, Account
from web3.providers.base import BaseProvider
from web3.middleware import geth_poa_middleware
import json
import argparse
import logging
from cb_wrapper import CBContracts
from utils.resource_manager import available_contracts

CC_ABI_PATH = 'crosscoin/build/contracts/CrossCoin.json'
CN_ABI_PATH = 'crosscoin/build/contracts/CrossNft.json'
PKEY_PATH = 'crosscoin/.secret'
CC_CONTRACT = available_contracts(100)['erc20'].address
CN_CONTRACT = available_contracts(100)['erc721'].address


def redeem_tokens(w3: BaseProvider, account: Account, quantity: int, type: CBContracts):
    if type == CBContracts.ERC20:
        addr = CC_CONTRACT
        abi_path = CC_ABI_PATH
    elif type == CBContracts.ERC721:
        addr = CN_CONTRACT
        abi_path = CN_ABI_PATH
    # Load contract abi
    with open(abi_path) as f:
        contract_abi = json.loads(f.read())
    abi = contract_abi['abi']
    contract = w3.eth.contract(address=addr, abi=abi)
    #w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    # Fire redeem transaction
    t_dict = {"chainId": w3.eth.chain_id,
              "nonce": w3.eth.get_transaction_count(account.address, 'pending'),
              "gasPrice": w3.toWei(10, "gwei"),
              "gas": 100000}
    tx = contract.functions.mint(
        account.address, quantity).buildTransaction(t_dict)
    signed_tx = w3.eth.account.sign_transaction(tx, account.key)
    tx_hash = w3.eth.send_raw_transaction(
        signed_tx.rawTransaction)
    logging.info(account.address + ' is redeeming ' + str(quantity) + ' on chain ' + str(
        t_dict['chainId']) + " tx_hash " + tx_hash.hex())
    tx_recipit = w3.eth.wait_for_transaction_receipt(tx_hash)
    logging.debug(tx_recipit)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(
        "Utility for interacting with erc721 contract.")
    parser.add_argument('--quantity', type=int, required=False, default=100)
    parser.add_argument('--endpoint', type=str, required=True)
    args = parser.parse_args()
    w3 = Web3(HTTPProvider(args.endpoint))
    with open(PKEY_PATH) as f:
        key = f.readline().strip()
    account = w3.eth.account.from_key(key)
    redeem_tokens(w3, account, args.quantity)
