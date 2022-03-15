//This deploys the fakelock erc20 handler. Tokens doesn't get locked after deposit.
const Erc20Handler = artifacts.require("FakeLockHandler");
const BridgeAddress = "0xAd28ab39509672F4D621206710654bd875D5fEa2"

module.exports = function (deployer) {  
  deployer.deploy(Erc20Handler, BridgeAddress);
};
