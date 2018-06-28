#!/bin/bash 


# get current directory
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

port=${RADIOPADRE_PORT:-$[$UID+9000]}
opts="--notebook-dir=. --port=$[$UID+9000]"

force_browser=""
bootstrap=""

while [ "$1" != "" ]; do
  if [ "$1" == "-h" -o "$1" == "--help" ]; then
    echo "Usage: $0 [-nb|--no-browser] [-b|--browser] [--bootstrap] [jupyter options] [notebook name]"
    exit 0
  elif [ "$1" == "-nb" -o "$1" == "--no-browser" ]; then
    opts="$opts --no-browser"
  elif [ "$1" == "-b" -o "$1" == "--browser" ]; then
    force_browser=1
  elif [ "$1" == "--bootstrap" ]; then
    bootstrap=1
  else
    opts="$opts $1"
  fi
  shift 1
done

if [ "$1" == "--bootstrap" ]; then
  bootstrap="yes"
else
  bootstrap="no"
fi

if which virtualenv >/dev/null && which pip >/dev/null; then
  echo "virtualenv and pip detected"
else
  echo "Radiopadre requires a working virtualenv and pip, sorry. Try apt install pip virtualenv?"
  exit 1
fi

radpadre_path="${0%/*}"
if [ "${radpadre_path#$HOME}" != "$radpadre_path" ]; then
  echo "Using (your own?) Radiopadre installation at $radpadre_path"
else
  echo "Using (systemwide?) Radiopadre installation at $radpadre_path"
fi

# this is where our virtualenv will reside
radpadre_venv=$HOME/.radiopadre-venv

if [ -f $radpadre_venv/bin/activate ]; then
  echo "Found radiopadre virtual environment in $radpadre_venv, activating"
  source $radpadre_venv/bin/activate
  echo "---"
else
  if [ "$bootstrap" != "" ]; then
    echo "The radiopadre virtual environment $radpadre_venv does not exist, creating it."
    virtualenv $radpadre_venv

    #launch virtual environment
    source $radpadre_venv/bin/activate

    #install the dependencies required for radiopadre
    if ! pip install -r $radpadre_path/requirements.txt; then
      echo "Some dependencies failed to install, see log above"
      exit 1
    fi
    echo "All dependencies installed in virtual environment"
    ipython kernel install --user --name=radiopadre
    echo "---"
  else
    echo "The radiopadre virtual environment $radpadre_venv does not exist. If you would like to create it,"
    echo "please re-run '$0 --bootstrap'. This may take a few minutes."  
    exit 1
  fi
fi

if [ ! -d .radiopadre ]; then
  if ! mkdir .radiopadre; then
    echo "Failed to create .radiopadre/"
    exit 1
  fi
fi

# add the directory where run-radiopadre.sh resides to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$DIR

echo "Welcome to Radiopadre! $DIR `pwd`"
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
    echo "Allowing jupyter notebook to open a web browser. Use -nb or --no-browser to disable."
  fi
fi
echo Available notebooks: `find . -maxdepth 1 -name "*.ipynb"`
echo
opts="$opts --ContentsManager.pre_save_hook=radiopadre.notebook_utils._notebook_save_hook"
opts="$opts --ContentsManager.allow_hidden=True"

echo "Command is: jupyter notebook $opts"
echo "Please wait a moment for jupyter to start up..."
jupyter notebook $opts &
pid=$!

# kill the server if remote connection closes
trap "kill -INT $pid" SIGINT SIGTERM SIGHUP

wait $pid
