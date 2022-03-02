pragma solidity >=0.8;

import "../node_modules/@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";

contract CrossNft is ERC721Enumerable {
    constructor() ERC721("CrossNft", "CN") {}

    function mint(address _beneficiary, uint256 _quantity) external {
        uint256 currentSupply = totalSupply();
        for (uint256 i = 0; i < _quantity; i++) {
            _safeMint(_beneficiary, currentSupply + i);
        }
    }
}
