// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "./BridgeToken.sol";

contract Destination is AccessControl {
    bytes32 public constant WARDEN_ROLE = keccak256("BRIDGE_WARDEN_ROLE");
    bytes32 public constant CREATOR_ROLE = keccak256("CREATOR_ROLE");

    mapping(address => address) public underlying_tokens; // underlying → wrapped
    mapping(address => address) public wrapped_tokens;   // wrapped → underlying
    address[] public tokens;

    event Creation(address indexed underlying_token, address indexed wrapped_token);
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

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(CREATOR_ROLE, admin);
        _grantRole(WARDEN_ROLE, admin);
    }

    /*//////////////////////////////////////////////////////////////
                        CREATE TOKEN
    //////////////////////////////////////////////////////////////*/

    function createToken(
        address _underlying_token,
        string memory name,
        string memory symbol
    ) public onlyRole(CREATOR_ROLE) returns (address) {

        require(_underlying_token != address(0), "Invalid underlying");
        require(underlying_tokens[_underlying_token] == address(0), "Already created");

        // Deploy new BridgeToken
        BridgeToken wrapped = new BridgeToken(
            _underlying_token,
            name,
            symbol,
            address(this)   // Destination contract = MINTER_ROLE admin
        );

        address wrappedAddr = address(wrapped);

        // Grant minting permission to Destination
        wrapped.grantRole(wrapped.MINTER_ROLE(), address(this));

        // Store mappings
        underlying_tokens[_underlying_token] = wrappedAddr;
        wrapped_tokens[wrappedAddr] = _underlying_token;
        tokens.push(wrappedAddr);

        emit Creation(_underlying_token, wrappedAddr);
        return wrappedAddr;
    }

    /*//////////////////////////////////////////////////////////////
                              WRAP
    //////////////////////////////////////////////////////////////*/

    function wrap(
        address _underlying_token,
        address _recipient,
        uint256 _amount
    ) public onlyRole(WARDEN_ROLE) {

        address wrappedAddr = underlying_tokens[_underlying_token];
        require(wrappedAddr != address(0), "Token not registered");

        BridgeToken(wrappedAddr).mint(_recipient, _amount);

        emit Wrap(
            _underlying_token,
            wrappedAddr,
            _recipient,
            _amount
        );
    }

    /*//////////////////////////////////////////////////////////////
                             UNWRAP
    //////////////////////////////////////////////////////////////*/

    function unwrap(
        address _wrapped_token,
        address _recipient,
        uint256 _amount
    ) public {

        require(_wrapped_token != address(0), "Invalid wrapped token");

        address underlyingAddr = wrapped_tokens[_wrapped_token];
        require(underlyingAddr != address(0), "Not a bridge token");

        // Burn caller's wrapped tokens
        BridgeToken(_wrapped_token).burn(msg.sender, _amount);

        emit Unwrap(
            underlyingAddr,
            _wrapped_token,
            msg.sender,
            _recipient,
            _amount
        );
    }
}