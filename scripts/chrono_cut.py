import time
import logging
from utils.ufw_mod import UFW, BLOCK, UNBLOCK

IP = "192.168.1.1"

if __name__=="__main__":
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting chrono ufw alter script.")
    ufw = UFW()
    for i in range(0,10):
        ufw.alter_config(BLOCK, IP)
        time.sleep(10)
        ufw.alter_config(UNBLOCK, IP)
        time.sleep(10)
