#!/bin/bash
set -ex
# SET THE FOLLOWING VARIABLES
# docker hub username
USERNAME=karaswinds
# image name
IMAGE=team_project_python
docker build -t $USERNAME/$IMAGE:latest .
version=`cat VERSION`
echo "version: $version"
docker tag $USERNAME/$IMAGE:latest $USERNAME/$IMAGE:$version
