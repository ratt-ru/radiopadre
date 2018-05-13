#!/usr/bin/python
'''
Script to initialise created virtual environment and run-radiopadre.sh script
Give script permissions to run using: chmod +x launcher.py
'''
import subprocess,os,sys

def detect_virtual():
	return hasattr(sys,'real_prefix')

print "Launching virtual environment"
print "*"*25

try:

	#get path to the virtual environment activation script
	cur_dir=os.getcwd() + '/radpadre_venv/bin/activate_this.py'

	print "Activating Virtual Environment"

	#executing the activation script
	execfile(cur_dir, dict(__file__=cur_dir))

	if detect_virtual():
		print "Virtual env launched"
	else:
		print "Virtual environment not found"


	#subprocess.call(['source',cur_dir])
	subprocess.call('./run-radiopadre.sh')

except KeyboardInterrupt:
	print "Exiting script"


