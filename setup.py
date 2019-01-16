from setuptools import setup
import os

__version__ = "0.4"

with open("requirements.txt") as stdr:
    install_requires = stdr.readlines()

scripts = ["bin/" + i for i in os.listdir("bin")]

setup(
    name="radiopadre",
    version=__version__,
    install_requires=install_requires,
    extras_require={"casacore" : ["python-casacore"] },
    author="Gijs Molenaar",
    author_email="gijs@pythonic.nl",
    description=("Helpers for visualizing resultsets in ipython notebook"),
    license="MIT",
    keywords="ipython notebook fits dataset resultset visualisation",
    url="http://github.com/radio-astro/radiopadre",
    packages=['radiopadre'],
    scripts=scripts,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
    ],
)
