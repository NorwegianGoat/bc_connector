pragma solidity >=0.8;

import "../node_modules/chainbridge-solidity/contracts/handlers/fee/BasicFeeHandler.sol";

contract FeeHandlerLockTime is BasicFeeHandler {
    uint256 private lastWithdraw;
    uint256 constant COOLDOWN = 7776000; // 6 months at 30 blocks per minute

    constructor(address bridgeAddress) BasicFeeHandler(bridgeAddress) {
        lastWithdraw = block.number;
    }

    function transferFee(
        address payable[] calldata addrs,
        uint256[] calldata amounts
    ) external override onlyAdmin {
        require(
            block.number >= lastWithdraw + COOLDOWN,
            "You need to wait before you can withdraw."
        );
        lastWithdraw = block.number;
        super.transferFee(addrs, amounts);
    }
}
