# Chain 0
import sqlite3
import time
from model.contract import Contract

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


def save_binding(resource_id: str, bridge: int, handler: int, target: int, chain: int):
    db = sqlite3.connect(BC_RESOURCES_PATH)
    cursor = db.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS binding (id INTEGER PRIMARY KEY AUTOINCREMENT, resource_id TEXT, bridge INTEGER, handler INTEGER, target INTEGER,chain INTEGER, timestamp INTEGER)''')
    cursor.execute(
        '''INSERT INTO binding(resource_id,bridge,handler,target,chain,timestamp) VALUES ('%s',%i,%i,%i,%i,%i)''' % (resource_id, bridge, handler, target, chain, int(time.time())))
    db.commit()


def available_contracts(chain: int):
    db = sqlite3.connect(BC_RESOURCES_PATH)
    cursor = db.cursor()
    contracts = cursor.execute(
        '''SELECT * FROM resources WHERE chain = %i ORDER BY timestamp DESC''' % chain)
    last_contracts = {}
    # Parses all contracts keeping only the last of each type
    for contract in contracts:
        if not last_contracts.get(contract[1]):
            last_contracts[contract[1]] = Contract(
                contract[0], contract[1], contract[2], contract[3], contract[4])
    return last_contracts


def available_resources(chain_id: int, target: int):
    db = sqlite3.connect(BC_RESOURCES_PATH)
    cursor = db.cursor()
    # TODO: Limitare all'ultimo bridge registrato per questa risorsa su questa chain order by date, limit 0
    return cursor.execute('''SELECT resource_id FROM binding WHERE chain = %i AND target = %i''' % (chain_id, target)).fetchone()[0]
