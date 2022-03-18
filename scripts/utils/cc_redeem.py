from web3 import HTTPProvider, Web3, Account
from web3.providers.base import BaseProvider
from web3.middleware import geth_poa_middleware
import json
import argparse
import logging
from model.contract import ContractTypes
from utils.resource_manager import available_contracts

CC_ABI_PATH = 'crosscoin/build/contracts/CrossCoin.json'
CN_ABI_PATH = 'crosscoin/build/contracts/CrossNft.json'
PKEY_PATH = 'crosscoin/.secret'


def _read_abi(abi_path: str):
    with open(abi_path) as f:
        contract_abi = json.loads(f.read())
    return contract_abi['abi']


def redeem_tokens(w3: BaseProvider, account: Account, quantity: int, type: ContractTypes):
    if type == ContractTypes.ERC20:
        addr = available_contracts(w3.eth.chain_id, ContractTypes.ERC20)['target'].address
        abi_path = CC_ABI_PATH
    elif type == ContractTypes.ERC721:
        addr = available_contracts(w3.eth.chain_id, ContractTypes.ERC721)['target'].address
        abi_path = CN_ABI_PATH
    abi = _read_abi(abi_path)
    contract = w3.eth.contract(address=addr, abi=abi)
    # Fire redeem transaction
    t_dict = {"chainId": w3.eth.chain_id,
              "nonce": w3.eth.get_transaction_count(account.address, 'pending'),
              "gasPrice": w3.toWei(10, "gwei"),
              "gas": 1000000}
    tx = contract.functions.mint(
        account.address, quantity).buildTransaction(t_dict)
    signed_tx = w3.eth.account.sign_transaction(tx, account.key)
    tx_hash = w3.eth.send_raw_transaction(
        signed_tx.rawTransaction)
    logging.info(account.address + ' is redeeming ' + str(quantity) + ' on chain ' + str(
        t_dict['chainId']) + " tx_hash " + tx_hash.hex())


def token_of_owner_by_index(w3:BaseProvider, address: str, index: int):
    abi_path = CN_ABI_PATH
    addr = available_contracts(w3.eth.chain_id, ContractTypes.ERC721)['target'].address
    abi = _read_abi(abi_path)
    contract = w3.eth.contract(address=addr, abi=abi)
    return contract.functions.tokenOfOwnerByIndex(address, index).call()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(
        "Utility for interacting with token contracts in crosscoin dir, the mint function is called and tokens are minted on chain.")
    parser.add_argument('--quantity', type=int, required=False, default=100)
    parser.add_argument('--endpoint', type=str, required=True)
    args = parser.parse_args()
    w3 = Web3(HTTPProvider(args.endpoint))
    with open(PKEY_PATH) as f:
        key = f.readline().strip()
    account = w3.eth.account.from_key(key)
    redeem_tokens(w3, account, args.quantity)
