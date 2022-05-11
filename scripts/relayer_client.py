from xmlrpc.client import ServerProxy

if __name__ == "__main__":
    # TODO: Read from config file
    with ServerProxy("http://192.168.1.3:23456") as proxy:
        resp = proxy.remap_relayer(
            "http://192.168.1.120:8545", 100, ["a", "b", "c"])
        print(resp)
