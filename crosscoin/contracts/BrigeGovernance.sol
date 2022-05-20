pragma solidity >=0.8;

// import "../node_modules/chainbridge-solidity/contracts/Bridge.sol";
// import "../node_modules/@openzeppelin/contracts/governance/Governor.sol";
import "../node_modules/@openzeppelin/contracts/governance/extensions/GovernorCountingSimple.sol";
import "../node_modules/@openzeppelin/contracts/utils/Context.sol";

contract BridgeGovernance is Context, GovernorCountingSimple {
    uint256 private quorumPercentage;
    uint256 private collateral;
    uint256 private nPartecipants = 0;
    mapping(address => bool) partecipants;

    event PartecipantJoined(address indexed partecipant, uint256 nPartecipants);

    modifier onlyPartecipant() {
        require(partecipants[_msgSender()], "You are not a partecipant.");
        _;
    }

    constructor(uint256 _quorum, uint256 _collateral)
        Governor("BridgeGovernance") payable
    {
        quorumPercentage = _quorum;
        collateral = _collateral;
        join(_msgSender());
    }

    // The user become a partecipant by sending a specific quantity
    // of money. In this way we enforce a correct behaviour.
    function join(address partecipant) public payable {
        require(
            msg.value == collateral,
            "You sent the wrong quantity to became a partecipant."
        );
        partecipants[partecipant] = true;
        nPartecipants += 1;
        emit PartecipantJoined(partecipant, nPartecipants);
    }

    //The quorum is a fraction of the partecipants
    function quorum(uint256 blockNumber)
        public
        view
        override
        returns (uint256)
    {
        return nPartecipants * (quorumPercentage / 100);
    }

    //Returns the number of votes associated to each partecipant,
    //in this implementation we use a fixed number.
    function getVotes(address account, uint256 blockNumber)
        public
        view
        override
        returns (uint256)
    {
        return 1;
    }

    function votingDelay() public pure override returns (uint256) {
        // for testing purposes we set 0 delay, but in a real context a slight delay would be better
        return 0;
        //return 6575; //one day (based on block production rate)
    }

    function votingPeriod() public pure override returns (uint256) {
        return 10;
        //return 46027; //one week
    }

    /**
     * @dev Part of the Governor Bravo's interface: _"The number of votes required in order for a voter to become a proposer"_.
     */
    function proposalThreshold() public view override returns (uint256) {
        return 0;
    }

    // Proposal function restricted only to partecipants who blocked funds.
    function propose(
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        string memory description
    ) public override onlyPartecipant returns (uint256) {
        return super.propose(targets, values, calldatas, description);
    }

    function castVote(uint256 proposalId, uint8 support)
        public
        virtual
        override
        onlyPartecipant
        returns (uint256)
    {
        return super.castVote(proposalId, support);
    }

    function castVoteWithReason(
        uint256 proposalId,
        uint8 support,
        string calldata reason
    ) public virtual override onlyPartecipant returns (uint256) {
        return super.castVoteWithReason(proposalId, support, reason);
    }

    function castVoteBySig(
        uint256 proposalId,
        uint8 support,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) public virtual override onlyPartecipant returns (uint256) {
        return super.castVoteBySig(proposalId, support, v, r, s);
    }
}
