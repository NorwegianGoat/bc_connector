import subprocess
from sys_mod import check_program

COMMAND = "truffle"

class Truffle():
    def __init__(self):
        if check_program(COMMAND):
            pass
        else:
            exit("Truffle seems not installed.")

    def deploy_contract(self):
        pass

