#!/bin/bash

#Run this file FIRST  to launch everything else
echo "Starting virtual environment..."

#redirect output from command command to nowhere
command -v virtualenv > /dev/null


if [ $? -eq 1 ]; then
	echo -e "virtualenv not found. Install? (y/n)\c"
	read
	if [ $REPLY = 'y' ]; then
		echo "Installing virtualenv"
		sudo apt-get install virtualenv
		echo -e "Done!\n\n"
	else
		echo -e "Exiting this script\n\n"
		exit
	fi
else 
	echo "virtualenv FOUND!"
fi

echo "Creating Virtual Environment"
virtualenv radpadre_venv

#launch virtual environment
source ./radpadre_venv/bin/activate

#install the dependencies required for radiopadre
pip install -r requirements.txt

echo "Modules installed in environment"


python ./launcher.py