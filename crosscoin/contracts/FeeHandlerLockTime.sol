pragma solidity >=0.8;

import "../node_modules/chainbridge-solidity/contracts/handlers/fee/BasicFeeHandler.sol";

contract FeeHandlerLockTime is BasicFeeHandler {
    uint256 private latestWithdraw;
    uint256 constant COOLDOWN = 7776000; // 6 months at 30 blocks per minute

    constructor(address bridgeAddress) BasicFeeHandler(bridgeAddress) {
        latestWithdraw = block.number;
    }

    function transferFee(
        address payable[] calldata addrs,
        uint256[] calldata amounts
    ) external override onlyAdmin {
        require(
            block.number >= latestWithdraw + COOLDOWN,
            "You need to wait before you can withdraw."
        );
        latestWithdraw = block.number;
        super.transferFee(addrs, amounts);
    }
}
