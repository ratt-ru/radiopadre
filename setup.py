import os
from setuptools import setup
from radiopadre import __version__


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

scripts = [ 'run-remote-padre', 'run-radiopadre.sh', 'run-radiopadre-docker.sh' ]

setup(
    name="radiopadre",
    version=__version__,
    author="Gijs Molenaar",
    author_email="gijs@pythonic.nl",
    description=("Helpers for visualizing resultsets in ipython notebook"),
    license="MIT",
    keywords="ipython notebook fits dataset resultset visualisation",
    url="http://github.com/radio-astro/radiopadre",
    packages=['radiopadre'],
    scripts=scripts,
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
    ],
)
