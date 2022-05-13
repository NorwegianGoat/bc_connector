from xmlrpc.client import ServerProxy

if __name__ == "__main__":
    SCR_CHAIN_NODE_ENDPOINT = "http://192.168.1.120:8545"
    BIDGE_CONTRACT = "0x3ab2A28A2a95FA7bbBdF8DfED9e6D945E99dDf38"
    RES_ID = "0xd8de56dd1db472be57d5840cb8d8d5961c69601e8d8d8a0c97a57c9ae8cb0f0f"
    with ServerProxy("http://192.168.1.110:23456") as proxy:
        resp = proxy.remap_relayer(
            SCR_CHAIN_NODE_ENDPOINT, 123, BIDGE_CONTRACT, RES_ID)
        print(resp)
