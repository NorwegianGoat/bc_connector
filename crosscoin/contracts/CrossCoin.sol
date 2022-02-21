pragma solidity >=0.8;

import "../node_modules/@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract CrossCoin is ERC20 {
    constructor() ERC20("CrossCoin", "CC") {}

    function mint(address beneficiary, uint256 quantity) external {
        _mint(beneficiary, quantity);
    }
}
