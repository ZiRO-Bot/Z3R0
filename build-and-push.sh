#!/bin/sh
VERSION="$(poetry version -s)"

sudo docker build -t debug -t ghcr.io/ziro-bot/z3r0 -t ghcr.io/ziro-bot/z3r0:$VERSION -f docker/Dockerfile . \
&& sudo docker push ghcr.io/ziro-bot/z3r0:latest \
&& sudo docker push ghcr.io/ziro-bot/z3r0:$VERSION
