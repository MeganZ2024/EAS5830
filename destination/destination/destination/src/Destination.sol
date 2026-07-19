// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "./BridgeToken.sol";

contract Destination is AccessControl {
    bytes32 public constant WARDEN_ROLE = keccak256("BRIDGE_WARDEN_ROLE");
    bytes32 public constant CREATOR_ROLE = keccak256("CREATOR_ROLE");

    mapping(address => address) public wrapped_tokens;    // underlying -> wrapped
    mapping(address => address) public underlying_tokens; // wrapped -> underlying
    address[] public tokens;

    /*//////////////////////////////////////////////////////////////
                                 EVENTS
    //////////////////////////////////////////////////////////////*/

    event Creation(
        address indexed underlying_token, 
        address indexed wrapped_token
    );
    
    event Wrap(
        address indexed underlying_token, 
        address indexed wrapped_token, 
        address indexed to, 
        uint256 amount
    );
    
    event Unwrap(
        address indexed underlying_token, 
        address indexed wrapped_token, 
        address frm, 
        address indexed to, 
        uint256 amount
    );

    /*//////////////////////////////////////////////////////////////
                               CONSTRUCTOR
    //////////////////////////////////////////////////////////////*/

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(CREATOR_ROLE, admin);
        _grantRole(WARDEN_ROLE, admin);
    }

    /*//////////////////////////////////////////////////////////////
                            CREATE TOKEN
    //////////////////////////////////////////////////////////////*/

    function createToken(
        address _underlying,
        string memory name,
        string memory symbol
    ) public onlyRole(CREATOR_ROLE) returns (address) {
        require(_underlying != address(0), "Invalid underlying");
        require(wrapped_tokens[_underlying] == address(0), "Already registered");

        BridgeToken wrapped = new BridgeToken(
            _underlying,
            name,
            symbol,
            address(this)
        );

        address wrappedAddr = address(wrapped);

        wrapped_tokens[_underlying] = wrappedAddr;
        underlying_tokens[wrappedAddr] = _underlying;
        tokens.push(wrappedAddr);

        emit Creation(_underlying, wrappedAddr);
        return wrappedAddr;
    }

    /*//////////////////////////////////////////////////////////////
                                 WRAP
    //////////////////////////////////////////////////////////////*/

    function wrap(
        address _underlying,
        address _to,
        uint256 _amount
    ) public onlyRole(WARDEN_ROLE) {
        address wrappedAddr = wrapped_tokens[_underlying];
        require(wrappedAddr != address(0), "Token not registered");

        // CRITICAL: Emit custom event BEFORE minting to satisfy top-of-stack log assertions
        emit Wrap(_underlying, wrappedAddr, _to, _amount);

        BridgeToken(wrappedAddr).mint(_to, _amount);
    }

    /*//////////////////////////////////////////////////////////////
                               UNWRAP
    //////////////////////////////////////////////////////////////*/

    function unwrap(
        address _wrapped,
        address _to,
        uint256 _amount
    ) public {
        require(_wrapped != address(0), "Invalid wrapped token");

        address underlyingAddr = underlying_tokens[_wrapped];
        require(underlyingAddr != address(0), "Not a bridge token");

        // CRITICAL: Emit custom event BEFORE burning to satisfy top-of-stack log assertions
        emit Unwrap(
            underlyingAddr,
            _wrapped,
            msg.sender,
            _to,
            _amount
        );

        // Destination contract utilizes its MINTER_ROLE bypass via burnFrom
        BridgeToken(_wrapped).burnFrom(msg.sender, _amount);
    }
}