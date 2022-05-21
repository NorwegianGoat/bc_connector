from xmlrpc.client import ServerProxy
import logging

SERVER_ENDPOINT = "http://192.168.1.110:23456"
SRC_CHAIN_NODE_ENDPOINT = "http://192.168.1.120:8545"
BIDGE_CONTRACT = "0x3ab2A28A2a95FA7bbBdF8DfED9e6D945E99dDf38"
RES_ID = "0xd8de56dd1db472be57d5840cb8d8d5961c69601e8d8d8a0c97a57c9ae8cb0f0f"

def ask_remap(server_endpoint:str, src_node_endpoint:str, from_block:int, bridge_addr:str, res_id:str ):
    with ServerProxy(server_endpoint) as proxy:
        response = proxy.remap_relayer(
            src_node_endpoint, from_block, bridge_addr, res_id)
        return response

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.info(ask_remap(SERVER_ENDPOINT, SRC_CHAIN_NODE_ENDPOINT, 100, BIDGE_CONTRACT, RES_ID))
