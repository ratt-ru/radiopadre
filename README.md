
Radiopadre: Python Astronomy Data & Results Examiner
=====================================================

Astronomy visualization framework for ipython notebooks.

[![Build Status](https://travis-ci.org/radio-astro/radiopadre.svg?branch=master](https://travis-ci.org/radio-astro/radiopadre)

[radiopadre on pypi](https://pypi.python.org/pypi/radiopadre)


Usage
-----

```
$ apt-get install imagemagick
$ pip install .
$ ./run-radiopadre.sh
```

Browse to ``http://localhost:8888``, or whatever port your ipython notebook says it binds to. Go into the 
notebooks folder and open the example notebook.

Using with your own data (locally)
----------------------------------

Copy ``example.ipynb`` or ``view-everything.ipynb`` into your data directory, and run ``run-radiopadre.sh`` from there.
You will probably want to customize the notebooks for your data. Refer to ``extended-example.ipynb``, and to 
the other notebooks in the repo for inspiration.

Using with your own data (remotely)
-----------------------------------

Say you have a remote machine called ``host`` to which you have SSH access, and you'd like to visualize stuff in 
``host:~/data``. Copy a radiopadre notebook to ``host:~/data``, then locally run

``run-remote-padre.py host:data/*.ipynb``

This will establish an SSH connection to ``host``, run a notebook server remotely, take care of port forwarding etc., 
and open a local browser session connecting you to the remote server.


Using with docker
-----------------

If you can't do the pip install above for whatever reason, you can use radiopadre with the radioastro/notebook docker 
container. Use the ```run-radiopadre-docker.sh``` script to run it with docker. NB: probably currently broken, please
report if so.

