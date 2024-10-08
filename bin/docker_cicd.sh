#!/bin/bash

docker build --build-arg TWINE_REPOSITORY_URL --build-arg TWINE_USERNAME --build-arg TWINE_PASSWORD -t fdci .
# docker run -it fdci
docker run fdci
