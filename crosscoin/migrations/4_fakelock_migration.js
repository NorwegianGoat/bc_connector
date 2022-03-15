//This deploys the fakelock erc20 handler. Tokens doesn't get locked after deposit.
const Erc20Handler = artifacts.require("FakeLockHandler");

module.exports = function (deployer) {
  deployer.deploy(Erc20Handler);
};
