pragma solidity >=0.8;

import "../node_modules/@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract CrossCoin is ERC20 {
    constructor() ERC20("CrossCoin", "CC") {}

    function mint(address _beneficiary, uint256 _quantity) external {
        _mint(_beneficiary, _quantity);
    }
}
