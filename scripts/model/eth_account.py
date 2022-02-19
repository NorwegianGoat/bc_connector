import logging 
from web3 import Account

class EthAcc():
    def __init__(self, key: str):
        self.account = Account().from_key(key)
        self.key = key
        logging.info("Address: " + self.get_address())

    def get_pkey(self) -> str:
        return self.key

    def get_address(self) -> str:
        return self.account.address