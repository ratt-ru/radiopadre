#!/bin/bash 

# get current directory
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

port=${RADIOPADRE_PORT:-$[$UID+9000]}
opts="--notebook-dir=. --port=$[$UID+9000]"

force_browser=""

while [ "$1" != "" ]; do
  if [ "$1" == "-h" -o "$1" == "--help" ]; then
    echo "Usage: $0 [-nb|--no-browser] [<notebook name>]"
    exit 0
  elif [ "$1" == "-nb" -o "$1" == "--no-browser" ]; then
    opts="$opts --no-browser"
  elif [ "$1" == "-b" -o "$1" == "--browser" ]; then
    force_browser=1
  else
    opts="$opts $1"
  fi
  shift 1
done

# add the directory where run-radiopadre.sh resides to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$DIR

echo "Welcome to radiopadre!"
echo
echo "I have chosen to use port $port for you. You may set RADIOPADRE_PORT if you prefer"
echo "it to use another port. Note that if another notebook is already open on that port,"
echo "ipython will pick an unused port instead. Check the output below to see if that is"
echo "the case."

if [ "$SSH_CLIENT" != "" -a "$force_browser" == "" ]; then
  opts="$opts --no-browser"
  echo
  echo "Since you're logged in via ssh, so I'm not opening a web browser for you. Please"
  echo "manually browse to localhost:$port. You will probably want to employ ssh port"
  echo "port forwarding if you want to browse this notebook from your own machine, e.g."
  echo "log in with"
  echo "          $ ssh -L $port:localhost$port user@machine"
else
  if ! echo $opts | grep -- --no-browser >/dev/null; then
    echo 
    echo "Allowing ipython notebook to open a web browser. Use -nb or --no-browser to disable."
  fi
fi

echo
opts="$opts --ContentsManager.pre_save_hook=radiopadre.notebook_utils._notebook_save_hook"

echo "Running ipython notebook $opts"
ipython notebook $opts &
pid=$!

# kill the server if remote connection closes
trap "kill -INT $pid" SIGINT SIGTERM SIGHUP

wait $pid
