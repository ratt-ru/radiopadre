#!/bin/bash

#Execute this file FIRST. It will launch everything else.

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
	echo "virtualenv FOUND"
fi

virtualenv radpadre_venv
#check for missing modules and install them
pip freeze > available_modules.txt
#copare the different files to see what needs to be installed
comm -3 <(sort available_modules.txt) <(sort requirements.txt) > download.txt
rm available_modules.txt
echo "Installing missing modules"
pip install -r download.txt

python ./launcher.py
