const BridgeGovernance = artifacts.require("BridgeGovernance");

module.exports = function (deployer) {
  deployer.deploy(BridgeGovernance);
};
