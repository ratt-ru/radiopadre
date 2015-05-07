import os
from setuptools import setup
from raviz import __version__


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="raviz",
    version=__version__,
    author="Gijs Molenaar",
    author_email="gijs@pythonic.nl",
    description=("Helpers for visualizing resultsets in ipython notebook"),
    license="MIT",
    keywords="ipython notebook fits dataset resultset visualisation",
    url="http://github.com/radio-astro/raviz",
    packages=['an_example_pypi_project', 'tests'],
    long_description=read('README'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
    ],
)