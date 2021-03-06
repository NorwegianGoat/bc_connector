pragma solidity >=0.8;

import "../node_modules/chainbridge-solidity/contracts/Bridge.sol";

contract BridgeWithdrawPatch is Bridge {
    // nonce -> chainId -> data
    mapping(uint64 => mapping(uint8 => bytes)) public _depositRecords;

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
        bytes calldata data,
        bytes calldata feeData
    ) external payable whenNotPaused {
        _deposit(destinationDomainID, resourceID, data, feeData);
        // Save deposit data
        uint64 depositNonce = _depositCounts[destinationDomainID];
        _depositRecords[depositNonce][destinationDomainID] = data;
    }

    function adminWithdraw(
        uint8 chainId,
        uint64 depositNonce,
        address handlerAddress,
        bytes memory data
    ) external onlyAdmin {
        // Data sent by admin
        address token;
        address recipient;
        uint256 amount;
        (token, recipient, amount) = abi.decode(
            data,
            (address, address, uint256)
        );
        // History
        bytes memory depositData = _depositRecords[depositNonce][chainId];
        uint256 depositAmount;
        uint256 addressLength;
        address sender;
        (depositAmount, addressLength, sender) = abi.decode(
            depositData,
            (uint256, uint256, address)
        );
        // Checks if the given data matches with the one saved for the deposit
        require(
            recipient == sender,
            "The refund must be sent to the original sender."
        );
        require(
            amount == depositAmount,
            "The refund amount has to be the same as the deposited one."
        );

        _adminWithdraw(handlerAddress, data);
    }
}
