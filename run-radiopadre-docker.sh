#!/bin/bash

#
# run-radiopadre-docker.sh
# 
# Runs radiopadre notebooks inside a docker container
#

echo "This will run radiopadre notebooks via docker"

DIR=${1:-`pwd`}

docker=${PADRE_DOCKER_EXEC:-docker}
docker_image=${PADRE_DOCKER_IMAGE:-radioastro/notebook}
port=${PADRE_DOCKER_PORT:-$[$UID+8000]}

if ! which $docker >/dev/null; then
  echo "$docker: no such executable. We need a working docker install!"
  echo "(If your docker is invoked as something else, please set the DOCKER_EXEC variable.)"
  exit 1
fi


if ! $docker images | grep $docker_image >/dev/null; then
  echo "Looks like the $docker_image docker image needs to be built."
  echo "This is a one-time operation that may take a few minutes, please be patient."
fi

echo "Will run radiopadre notebooks (via $docker_image) on $DIR."
echo "The notebook server will be available on port $port, set PADRE_DOCKER_PORT to override."
echo "Point your browser to localhost:$port"

if ! cd $DIR; then
  echo "Can't cd into $DIR, sorry."
  exit 1
fi

if [ "$PADRE_NOTEBOOK_DIR" != "" ]; then
  echo "Caution, your $PADRE_NOTEBOOK_DIR will be mounted inside the container"
  volumes="-v $PADRE_NOTEBOOK_DIR:/notebooks:rw"
fi

DIR=${DIR%/}
container_dirname=${DIR##*/}

docker run -it -p $port:8888 \
                $volumes \
                -v $DIR:/notebooks/$container_dirname:rw \
                -e PADRE_DATA_DIR=/notebooks/$container_dirname \
                -e PADRE_ORIGINAL_DIR=$DIR \
                -e PADRE_NOTEBOOK_DIR=/notebooks \
                $docker_image 
