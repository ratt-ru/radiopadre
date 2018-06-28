#!/bin/bash 

yn_prompt()
{
	echo -e "$1 (y/n)"
	read
	if [ $REPLY = 'y' ]; then
	  return 0
	fi
	return 1
}

# Check for virtualenv first
command -v virtualenv > /dev/null

if [ $? -eq 1 ]; then
  if ! yn_prompt "virtualenv not found. Install with apt-get?"; then
    echo -e "Radiopadre requires a working virtualenv, sorry."
    exit 1 
  fi
  echo "Installing virtualenv"
  if ! sudo apt-get install virtualenv; then
    echo "virtualenv installation failed, see log above"
    exit 1
  fi
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
  echo "Creating radiopadre virtual environment in $radpadre_venv and installing dependencies"
  if ! yn_prompt "This is a one-off operation, and may take a few minutes. Proceed?"; then
    exit 1
  fi
  echo "OK, proceeding..."
  virtualenv $radpadre_venv

  #launch virtual environment
  source $radpadre_venv/bin/activate

  #install the dependencies required for radiopadre
  if ! pip install -r $radpadre_path/requirements.txt; then
    echo "Some dependencies failed to install, see log above"
    exit 1
  fi
  echo "All dependencies installed in virtual environment"
  echo "---"
fi


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

echo "Running jupyter notebook $opts"
jupyter notebook $opts &
pid=$!

# kill the server if remote connection closes
trap "kill -INT $pid" SIGINT SIGTERM SIGHUP

wait $pid
