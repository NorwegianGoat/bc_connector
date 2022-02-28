class Contract():
    def __init__(self, id: int, type: str, address: str, chain: int, deployed_on: int):
        self.id = id
        self.type = type
        self.address = address
        self.chain = chain
        self.deployed_on = deployed_on

    def __repr__(self) -> str:
        return self.address