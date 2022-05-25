pragma solidity >=0.8;

import "../node_modules/chainbridge-solidity/contracts/Bridge.sol";
import "../node_modules/@openzeppelin/contracts/utils/Context.sol";

contract BridgeWithdrawPatch is Context, Bridge {
    struct DepositItem {
        uint256 amount;
        address sender;
    }

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
        bytes calldata data
    ) external payable override whenNotPaused {
        super.deposit(destinationDomainID, resourceID, data);
        // Saves deposit data
        uint256 amount = abi.decode(data, (uint256));
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
        bytes depositData = _depositRecords[depositNonce][chainId];
        uint256 deposit;
        uint256 addressLength;
        address sender;
        (amount, addressLength, sender) = abi.decode(
            depositData,
            (uint256, uint256, address)
        );
        // Checks if the given data matches with the one saved for the deposit
        require(
            recipient == sender,
            "The refund must be sent to the original sender."
        );
        require(
            amount == deposit,
            "The refund amount has to be the same as the deposited one."
        );

        _adminWithdraw(handlerAddress, data);
    }
}
