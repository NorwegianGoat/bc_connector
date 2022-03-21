// Deploys the latest version of the bridge contract made by chainbridge
// the bridge included in the latest version of cb-sol-cli does not
// include the method adminSetNonce and has different function
// parameters in the adminWithdraw method.
const Bridge = artifacts.require("Bridge");
const relayers = ['0x222b8e2152E189f5282249877e039EF2c1c0C826']

module.exports = function (deployer) {
    deployer.deploy(Bridge, 45, relayers, 1, 0, 0);
};