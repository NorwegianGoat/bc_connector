# Chain 0
import sqlite3
import time
C0_BRIDGE_ADDRESS = '0x3ab2A28A2a95FA7bbBdF8DfED9e6D945E99dDf38'
C0_ERC20_HANDLER = "0xC671538D5A6BccAe6cB931008fFC45F9328290fd"
C0_ERC20 = '0x4Aa451d788970B7521BE3A49cA2EebFCb1Aa3c70'
# Binds the tokens between the two chains
RESOURCE_ID_NFT = '0x000000000000000000000000000000c76ebe4a02bbc34786d860b355f5a5ce00'
RESOURCE_ID_ERC20 = '0x79e5d22d1fd140f502eee0fa2b82fc909562e9b809cb78beffdefccad9717385'
# Chain 1
C1_BRIDGE_ADDRESS = '0x3ab2A28A2a95FA7bbBdF8DfED9e6D945E99dDf38'
C1_ERC20_HANDLER = "0xC671538D5A6BccAe6cB931008fFC45F9328290fd"
C1_ERC20 = '0x4Df5040aEe6822815D9Acb9276934102b1A72165'


BC_RESOURCES_PATH = 'bc_resources.db'


def _parse_blob(lines: bytes, chain: int):
    lines = lines.decode('UTF-8').splitlines()
    ret = []
    for line in lines:
        if "Bridge:" in line or "Erc20 Handler:" in line or "Erc721 Handler:" in line or "Generic Handler:" in line or "Erc20:" in line or "Erc721:" in line:
            partition = list(line.replace(
                " ", "").replace(':', ",").partition(","))
            contract_name = partition[0]
            partition[0] = contract_name[0].lower() + contract_name[1:]
            partition += [',', chain, ',', int(time.time())]
            if 'NotDeployed' not in partition:
                ret.append(partition)
    return ret


def save_contracts(lines: str, chain: int):
    contracts = _parse_blob(lines, chain)
    db = sqlite3.connect(BC_RESOURCES_PATH)
    cursor = db.cursor()
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS resources (id INTEGER PRIMARY KEY AUTOINCREMENT, contract TEXT, address TEXT, chain INTEGER, timestamp INTEGER)''')
    for contract in contracts:
        cursor.execute(
            '''INSERT INTO resources(contract,address,chain,timestamp) VALUES ('%s','%s',%i,%i)''' % (contract[0], contract[2], contract[4], contract[6]))
    db.commit()


def available_contracts():
    pass
