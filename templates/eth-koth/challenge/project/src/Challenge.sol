// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

contract Challenge {
    address public immutable PLAYER;

    uint private clicks;

    constructor(address player) {
        PLAYER = player;
    }

    function click() external {
        clicks++;
    }

    function getScore() external view returns (uint256) {
        return clicks;
    }
}
