const BridgeGovernance = artifacts.require("BridgeGovernance");
//Quorum is fixed at 50%
const Quorum = 50
//1 of the chain currency is requested to join
const Collateral = 1

module.exports = function (deployer) {
  deployer.deploy(BridgeGovernance, Quorum, Collateral);
};
