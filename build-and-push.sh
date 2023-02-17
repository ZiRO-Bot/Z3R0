#!/bin/sh
VERSION="$(poetry version -s)"
STAGE="0"  # 0 = development, 1 = production
TAG="ghcr.io/ziro-bot/z3r0"

sudo docker build -t debug $(test "$STAGE" = "1" && echo "-t $TAG:latest -t $TAG:$VERSION" || echo "-t $TAG:nightly") -f docker/Dockerfile . \
&& test "$STAGE" = "1" && $(sudo docker push $TAG:$VERSION && sudo docker push $TAG:latest) \
|| sudo docker push $TAG:nightly
