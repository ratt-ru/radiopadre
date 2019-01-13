#!/bin/bash

#Run this file FIRST  to launch everything else
#echo "Starting virtual environment..."

#redirect output from command command to nowhere
command -v virtualenv > /dev/null


if [ $? -eq 1 ]; then
	echo -e "virtualenv not found. Install with apt-get? (y/n)\c"
	read
	if [ $REPLY = 'y' ]; then
		echo "Installing virtualenv"
		sudo apt-get install virtualenv
		echo -e "Done!\n\n"
	else
		echo -e "Can't proceed without virtualenv"
		exit 1
	fi
else 
	echo "virtualenv FOUND!"
fi

radpadre_venv=$HOME/.radpadre_venv

radpadre_path="${0%/*}"
echo "Using Radiopadre installation at $radpadre_path"

if [ -f $radpadre_venv/bin/activate ]; then
  echo "Using radiopadre virtual environment in $radpadre_venv"
  source ./radpadre_venv/bin/activate
else
  echo "Creating radiopadre virtual environment and installing dependencies"
  virtualenv $radpadre_venv

  #launch virtual environment
  source ./radpadre_venv/bin/activate

  #install the dependencies required for radiopadre
  if ! pip install -r $radpadre_path/requirements.txt; then
    echo "Some dependencies failed to install, see log above"
    exit 1
  fi

  echo "All dependencies installed in virtual environment"
fi

exec python $radpadre_path/run-radiopadre.sh

#exec python $radpadre_path/launcher.py
