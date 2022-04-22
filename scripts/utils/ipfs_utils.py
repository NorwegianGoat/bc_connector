import subprocess
import ipfsApi
from sys_mod import check_program

COMMAND = "ipfs"


class IPFS():
    def __init__(self, host: str = "127.0.0.1", port: int = 5001) -> None:
        if check_program(COMMAND):
            subprocess.run(['nohup', COMMAND, "daemon", "&"])
            self.client = ipfsApi.Client(host, port)
        else:
            exit(
                "IPFS desktop seems not to be installed. Run apt-get install ipfs-desktop.")

    def add_storage(self, file_path: str):
        self.client.add(file_path)


if __name__ == "__main__":
    client = IPFS()
    client.add_storage("./cb_wrapper.py")
