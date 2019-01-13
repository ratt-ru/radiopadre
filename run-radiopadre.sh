#!/bin/bash 


# get current directory
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

# port=${RADIOPADRE_PORT:-$[$UID+9000]}
# --port=0" # $[$UID+9000]"

opts="--notebook-dir=."

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
    ln -s $radpadre_venv/js9-www .radiopadre/js9-www
fi

# add the directory where run-radiopadre.sh resides to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$DIR

echo "Welcome to Radiopadre! $DIR `pwd`"
echo

if [ "$SSH_CLIENT" != "" -a "$force_browser" == "" ]; then
  opts="$opts --no-browser"
  echo
  echo "Since you're logged in via ssh, so I'm not opening a web browser for you. Please"
  echo "manually browse to the URL printed by Jupyter below. You will probably want to employ ssh port"
  echo "port forwarding if you want to browse this notebook from your own machine."
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
opts="$opts --NotebookApp.allow_origin='*'"

echo "Starting: nodejs $radpadre_path/js9-www/js9Helper.js"
DEBUG='*' nodejs $radpadre_path/js9-www/js9Helper.js &
helper_pid=$!

echo "Starting: python -m SimpleHTTPServer 0"
python -m SimpleHTTPServer 0 &
serv_pid=$!

echo "Starting: jupyter notebook $opts"
echo "Please wait a moment for jupyter to start up..."
jupyter notebook $opts &
jup_pid=$!

# kill the server if remote connection closes
trap "(echo `date`: will kill -INT $jup_pid $serv_pid $helper_pid; kill -INT $jup_pid; kill -INT $serv_pid; kill $helper_pid) 2>&1 1>>.radiopadre/log" SIGINT SIGTERM SIGHUP

wait # $pid $serv_pid $helper_pid

echo "`date`: Wait done, exiting main script" >>.radiopadre/log