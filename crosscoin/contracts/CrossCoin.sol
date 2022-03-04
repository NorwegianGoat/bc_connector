pragma solidity >=0.8;

import "../node_modules/@openzeppelin/contracts/token/ERC20/presets/ERC20PresetMinterPauser.sol";

contract CrossCoin is ERC20PresetMinterPauser {
    constructor() ERC20PresetMinterPauser("CrossCoin", "CC") {}
}
