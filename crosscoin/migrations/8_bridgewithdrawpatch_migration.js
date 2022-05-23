//This deploys the fakelock erc20 handler. Tokens doesn't get locked after deposit.
const BridgeWithdrawPatch = artifacts.require("BridgeWithdrawPatch");
const DomainId = 100
const InitialRelayers = 1
const InitialRelayerThreshold = 1
const Fee = 0
const Expiry = 0

module.exports = function (deployer) {
  deployer.deploy(BridgeWithdrawPatch, DomainId, InitialRelayers, InitialRelayerThreshold, Fee, Expiry);
};
