
Radio padre: Python Astronomy Data & Results Examiner
=====================================================

Functions and helpers for displaying FITS images etc. in an ipython notebook.

[![Build Status](https://travis-ci.org/radio-astro/radiopadre.svg?branch=v0.1.2)](https://travis-ci.org/radio-astro/radiopadre)

[radiopadre on pypi](https://pypi.python.org/pypi/radiopadre)


Usage
-----

```
$ apt-get install imagemagick
$ pip install -r requirements.txt
$ ./run-radiopadre.sh
```

Browse to http://localhost:8888, or whatever port your ipython notebooksays it binds to. Go into the 
notebooks folder and open the example notebook.

Using with your own data
------------------------

Copy example.ipynb or view-everything.ipynb into your data directory, and run run-radiopadre.sh from there.
You will probably want to customize the notebooks for your data. Refer to extended-example.ipynb, and to 
the other notebooks in the repo for inspiration.

Using with docker
-----------------

If you can't do the pip install above for whatever reason, you can use radiopadre with the radioastro/notebook docker container. Use the ```run-radiopadre-docker.sh``` script to run it with docker.

