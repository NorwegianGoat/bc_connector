const { networks } = require('../truffle-config.js')

const Erc20 = artifacts.require("CrossCoin");
const Erc20Handler = artifacts.require("node_modules/chainbridge-solidity/contracts/handlers/ERC20Handler")
const BridgeWithdrawPatch = artifacts.require("BridgeWithdrawPatch");
const RootBoard = artifacts.require("RootBoard");
const BridgeGovernance = artifacts.require("BridgeGovernance");
const FeeHandler = artifacts.require("FeeHandlerLockTime");


module.exports = function (deployer, network) {
  //Token contract deploy
  deployer.deploy(Erc20);
  //Bridge + handler deploy
  const DomainId = networks[network].network_id
  const InitialRelayers = ['0x222b8e2152E189f5282249877e039EF2c1c0C826']
  const InitialRelayerThreshold = 1
  const Fee = 0
  const Expiry = 100
  deployer.deploy(BridgeWithdrawPatch, DomainId, InitialRelayers, InitialRelayerThreshold, Fee, Expiry).then(function () {
    return deployer.deploy(Erc20Handler, BridgeWithdrawPatch.address);
  });
  //Root board deploy
  deployer.deploy(RootBoard);
  //FeeHandler deploy
  deployer.deploy(FeeHandler, BridgeWithdrawPatch.address);
  //Governance deploy
  const Quorum = 66
  const Collateral = "1000000000000000000"
  deployer.deploy(BridgeGovernance, Quorum, Collateral,
    { value: Collateral });
};