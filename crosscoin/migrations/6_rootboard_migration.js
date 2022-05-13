const RootBoard = artifacts.require("RootBoard");

module.exports = function (deployer) {
  deployer.deploy(RootBoard);
};
