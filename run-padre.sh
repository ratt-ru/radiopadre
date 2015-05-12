#!/bin/bash 

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
# add the directory where run-padre.sh resides to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$DIR

port=${PADRE_PORT:-$[$UID+9000]}

if [ "$SSH_CLIENT" != "" ]; then
  opts="--no-browser"
  echo "Welcome to padre!"
  echo
  echo "I have chosen to use port $port for you. You may set PADRE_PORT if you prefer it to"
  echo "use another port. Note that if another notebook is already open on that port,"
  echo "ipython will pick an unused port instead. Check the output below to see if that"
  echo "is the case."
  echo
  echo "Since you're logged in via ssh, so I'm not opening a web browser for you. Please"
  echo "manually browse to localhost:$port. You will probably want to employ ssh"
  echo "port forwarding if you want to browse this notebook from your own machine, "
  echo "e.g. log in with"
  echo "          $ ssh -L $port:localhost$port user@machine"
  echo 
else
  opts=""
fi

ipython notebook --notebook-dir=. --port=$[$UID+9000] $opts
