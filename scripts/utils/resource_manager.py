import sqlite3
import time
from model.contract import Contract, ContractTypes
import logging

BC_RESOURCES_PATH = 'resources/bc_resources.db'


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


def add_contract(ctype: ContractTypes, address: str, chain_id: int, timestamp: int):
    db = sqlite3.connect(BC_RESOURCES_PATH)
    cursor = db.cursor()
    cursor.execute(
        '''INSERT INTO resources(contract,address,chain,timestamp) VALUES ('%s','%s',%i,%i)''' % (ctype, address, chain_id, timestamp))
    db.commit()

def save_contracts(lines: str, chain: int):
    contracts = _parse_blob(lines, chain)
    db = sqlite3.connect(BC_RESOURCES_PATH)
    cursor = db.cursor()
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS resources (id INTEGER PRIMARY KEY AUTOINCREMENT, contract TEXT, address TEXT, chain INTEGER, timestamp INTEGER)''')
    for contract in contracts:
        add_contract(contract[0], contract[2], contract[4], contract[6])


def save_binding(resource_id: str, bridge: int, handler: int, target: int, chain: int):
    db = sqlite3.connect(BC_RESOURCES_PATH)
    cursor = db.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS binding (id INTEGER PRIMARY KEY AUTOINCREMENT, resource_id TEXT, bridge INTEGER, handler INTEGER, target INTEGER,chain INTEGER, timestamp INTEGER)''')
    cursor.execute(
        '''INSERT INTO binding(resource_id,bridge,handler,target,chain,timestamp) VALUES ('%s',%i,%i,%i,%i,%i)''' % (resource_id, bridge, handler, target, chain, int(time.time())))
    db.commit()


def _contract_alias(name: str):
    if name == ContractTypes.ERC20_HANDLER or name == ContractTypes.ERC721_HANDLER:
        return "handler"
    if name == ContractTypes.ERC20 or name == ContractTypes.ERC721:
        return "target"
    else:
        return "bridge"


def available_contracts(chain: int, type: ContractTypes):
    db = sqlite3.connect(BC_RESOURCES_PATH)
    cursor = db.cursor()
    contracts = cursor.execute(
        '''SELECT * FROM resources WHERE chain = %i ORDER BY timestamp DESC''' % chain)
    last_contracts = {}
    # Parses all contracts keeping only the last of each type
    for contract in contracts:
        # If this type of contract is not in the dict it means that it is the most
        # recent of its type
        if not last_contracts.get(_contract_alias(contract[1])):
            if type:
                # If this is the bridge contract or the type for wich the user
                # is filtering we add to the list of contracts
                if type in contract[1] or contract[1] == ContractTypes.BRIDGE:
                    last_contracts[_contract_alias(contract[1])] = Contract(
                        contract[0], contract[1], contract[2], contract[3], contract[4])
            else:
                # User wants to retreive all the most recent contracts, so we add
                # all the contracts on this chain
                last_contracts[_contract_alias(contract[1])] = Contract(
                    contract[0], contract[1], contract[2], contract[3], contract[4])
    return last_contracts


def available_resources(chain_id: int, target: int):
    db = sqlite3.connect(BC_RESOURCES_PATH)
    cursor = db.cursor()
    res_id = cursor.execute('''SELECT resource_id FROM binding WHERE chain = %i AND target = %i ORDER BY timestamp DESC LIMIT 1''' % (
        chain_id, target)).fetchone()[0]
    logging.info("Res id for target %i is %s" % (target, res_id))
    return res_id
