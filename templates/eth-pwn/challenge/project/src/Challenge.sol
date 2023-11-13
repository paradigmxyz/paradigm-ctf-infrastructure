// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

contract Challenge {
    address public immutable PLAYER;

    bool private solved;

    constructor(address player) {
        PLAYER = player;
    }

    function solve() external {
        solved = true;
    }

    function isSolved() external view returns (bool) {
        return solved;
    }
}
