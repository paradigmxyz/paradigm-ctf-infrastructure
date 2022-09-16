#!/bin/bash

(cd challenge-base && docker buildx build --push --platform linux/amd64 . -t gcr.io/paradigmxyz/ctf/base:latest)
(cd eth-challenge-base && docker buildx build --push --platform linux/amd64 . -t gcr.io/paradigmxyz/ctf/eth-base:latest)
(cd cairo-challenge-base && docker buildx build --push --platform linux/amd64 . -t gcr.io/paradigmxyz/ctf/cairo-base:latest)
