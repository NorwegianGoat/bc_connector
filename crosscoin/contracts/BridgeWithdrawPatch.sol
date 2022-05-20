pragma solidity >=0.8;

import "../node_modules/chainbridge-solidity/contracts/Bridge.sol";
import "../node_modules/@openzeppelin/contracts/utils/Context.sol";

contract BridgeWithdrawPatch is Bridge, Context {
    struct Deposit {
        uint256 amount;
        address sender;
    }

    // ChainId -> nonce -> data
    mapping(uint256 => mapping(uint256 => Deposit)) depositHistory;

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
        uint256 amount = abi.decode(data, (uint256));
        // Saves deposit data
        uint64 depositNonce = _depositCounts[destinationDomainID];
        depositHistory[destinationDomainID][depositNonce + 1] = Deposit(
            amount,
            _msgSender()
        );

        super.deposit(destinationDomainID, resourceID, data);
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
        (tokenAddress, recipient, amount) = abi.decode(
            data,
            (address, address, uint256)
        );
        Deposit depositData = depositHistory[chainId][depositNonce];
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
