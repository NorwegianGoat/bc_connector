pragma solidity >=0.8;

import "../node_modules/chainbridge-solidity/contracts/handlers/ERC20Handler.sol";

contract FakeLockHandler is ERC20Handler {
    constructor(address bridgeAddress) ERC20Handler(bridgeAddress) {}

    function deposit(
        bytes32 resourceID,
        address depositer,
        bytes calldata data
    ) external override onlyBridge returns (bytes memory) {
        uint256 amount;
        (amount) = abi.decode(data, (uint256));

        address tokenAddress = _resourceIDToTokenContractAddress[resourceID];
        require(
            _contractWhitelist[tokenAddress],
            "provided tokenAddress is not whitelisted"
        );
        // No token gets burned or locked.
        if (_burnList[tokenAddress]) {
            burnERC20(tokenAddress, depositer, 0);
        } else {
            lockERC20(tokenAddress, depositer, address(this), 0);
        }
    }
}
