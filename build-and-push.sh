#!/bin/sh
STAGE="alpha"
VERSION="$(poetry version -s)-$STAGE"

sudo docker build -t debug -t ghcr.io/ziro-bot/z3r0 -t ghcr.io/ziro-bot/z3r0:$VERSION ./

sudo docker push ghcr.io/ziro-bot/z3r0:latest
sudo docker push ghcr.io/ziro-bot/z3r0:$VERSION
