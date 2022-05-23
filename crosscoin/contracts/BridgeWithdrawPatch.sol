pragma solidity >=0.8;

import "../node_modules/chainbridge-solidity/contracts/Bridge.sol";
import "../node_modules/@openzeppelin/contracts/utils/Context.sol";

contract BridgeWithdrawPatch is Context, Bridge {
    struct DepositItem {
        uint256 amount;
        address sender;
    }

    // ChainId -> nonce -> data
    mapping(uint256 => mapping(uint256 => DepositItem)) depositHistory;

    constructor(
        uint8 domainID,
        address[] memory initialRelayers,
        uint256 initialRelayerThreshold,
        uint256 fee,
        uint256 expiry
    ) Bridge(domainID, initialRelayers, initialRelayerThreshold, fee, expiry) {}

    function deposit(
        uint8 destinationDomainID,
        bytes32 resourceID,
        bytes calldata data
    ) external payable override whenNotPaused {
        super.deposit(destinationDomainID, resourceID, data);
        // Saves deposit data
        uint256 amount = abi.decode(data, (uint256));
        uint64 depositNonce = _depositCounts[destinationDomainID];
        depositHistory[destinationDomainID][depositNonce] = DepositItem(
            amount,
            _msgSender()
        );
    }

    function adminWithdraw(
        uint8 chainId,
        uint64 depositNonce,
        address handlerAddress,
        bytes memory data
    ) external override onlyAdmin {
        address token;
        address recipient;
        uint256 amount;
        (token, recipient, amount) = abi.decode(
            data,
            (address, address, uint256)
        );
        DepositItem memory depositData = depositHistory[chainId][depositNonce];
        // Checks if the given data matches with the one saved for the deposit
        require(
            recipient == depositData.sender,
            "The refund must be sent to the original sender."
        );
        require(
            amount == depositData.amount,
            "The refund amount has to be the same as the deposited one."
        );

        super.adminWithdraw(handlerAddress, data);
    }
}
