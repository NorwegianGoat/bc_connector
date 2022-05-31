const Erc20 = artifacts.require("CrossCoin");
const Erc20Handler = artifacts.require("node_modules/chainbridge-solidity/contracts/handlers/ERC20Handler")
const BridgeWithdrawPatch = artifacts.require("BridgeWithdrawPatch");
const RootBoard = artifacts.require("RootBoard");
const BridgeGovernance = artifacts.require("BridgeGovernance");

/*
* Token contract deploy
*/
module.exports = function (deployer) {
  deployer.deploy(Erc20);
};

/*
* Bridge + handler deploy
*/
module.exports = function (deployer) {
  const DomainId = 100
  const InitialRelayers = ['0x222b8e2152E189f5282249877e039EF2c1c0C826']
  const InitialRelayerThreshold = 1
  const Fee = 1
  const Expiry = 0
  deployer.deploy(BridgeWithdrawPatch, DomainId, InitialRelayers, InitialRelayerThreshold, Fee, Expiry).then(function () {
    return deployer.deploy(Erc20Handler, BridgeWithdrawPatch.address);
  });
};

/*
* Root board deploy
*/
module.exports = function (deployer) {
  deployer.deploy(RootBoard);
};

/*
* Governance deploy
*/
module.exports = function (deployer) {
  const Quorum = 50
  const Collateral = "1000000000000000000"
  deployer.deploy(BridgeGovernance, Quorum, Collateral,
    { value: Collateral });
};



