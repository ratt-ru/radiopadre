#!/bin/bash 

export PYTHONPATH=`pwd`

if [ "$SSH_CLIENT" != "" ]; then
  opts="--no-browser"
  echo "You're logged in via ssh, so I'm not opening a web browser for you. Please"
  echo "manually browse to the indicated URL. You will probably want to employ ssh"
  echo "port forwarding if you want to browse a remote notebook from your own machine."
  
else
  opts = ""
fi

ipython notebook --notebook-dir=. $opts
