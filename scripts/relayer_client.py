from xmlrpc.client import ServerProxy

if __name__ == "__main__":
    # TODO: Read from config file
    with ServerProxy("http://192.168.1.110:23456") as proxy:
        resp = proxy.remap_relayer(
            "http://192.168.1.120:8545", 123, ["0x3ab2A28A2a95FA7bbBdF8DfED9e6D945E99dDf38",
                                                    "0xC671538D5A6BccAe6cB931008fFC45F9328290fd",
                                                    "0x4Df5040aEe6822815D9Acb9276934102b1A72165"])
        print(resp)
