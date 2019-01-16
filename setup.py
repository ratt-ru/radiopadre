from setuptools import setup
import os

__version__ = "0.4"

install_requires = [
    'nbformat',
    'jupyter',
    'ipython>3.0',
    'notebook',
    'matplotlib>=1.3',
    'astropy',
    'aplpy',
    'tornado>=4.0',
    'jsonschema',
    'terminado',
    'setuptools',
    'pyzmq',
    'jinja2',
]

scripts = ["bin/" + i for i in os.listdir("bin")]

setup(
    name="radiopadre",
    version=__version__,
    install_requires=install_requires,
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
