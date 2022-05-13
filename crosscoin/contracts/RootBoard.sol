pragma solidity >=0.8;

import "../node_modules/@openzeppelin/contracts/access/Ownable.sol";

contract RootBoard is Ownable {
    struct MerkleRoot {
        uint256 latestDepositNonce;
        string trieRoot;
    }

    //chainId -> latest merkleRoot
    mapping(uint256 => MerkleRoot) private chainRoots;

    constructor() Ownable() {}

    function getLatestRoot(uint256 _chainId)
        public
        view
        returns (MerkleRoot memory)
    {
        return chainRoots[_chainId];
    }

    function setLatestRoot(
        uint256 _chainId,
        uint256 _nonce,
        string calldata _root
    ) external onlyOwner {
        //checks the nonce is not downgraded
        MerkleRoot memory lastDeposit = chainRoots[_chainId];
        require(
            lastDeposit.latestDepositNonce < _nonce,
            "Nonce downgrade is not permitted!"
        );
        chainRoots[_chainId] = MerkleRoot(_nonce, _root);
    }
}
