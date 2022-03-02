from enum import Enum


class ContractTypes(str, Enum):
    BRIDGE = "bridge"
    ERC20_HANDLER = "erc20Handler"
    ERC20 = "erc20"
    ERC721_HANDLER = "erc721Handler"
    ERC721 = "erc721"
    GENERIC_HANDLER = "genericHandler"


class Contract():
    def __init__(self, id: int, type: ContractTypes, address: str, chain: int, deployed_on: int):
        self.id = id
        self.type = type
        self.address = address
        self.chain = chain
        self.deployed_on = deployed_on

    def __repr__(self) -> str:
        return self.address
