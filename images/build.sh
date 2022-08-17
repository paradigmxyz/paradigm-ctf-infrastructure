#!/bin/bash

(cd challenge_base && docker build -t gcr.io/paradigmxyz/ctf/base:latest .)
(cd eth_challenge_base && docker build -t gcr.io/paradigmxyz/ctf/eth-base:latest .)
