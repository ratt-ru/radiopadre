from setuptools import setup
import os

__version__ = "1.0~pre2"

with open("requirements.txt") as stdr:
    install_requires = stdr.readlines()

scripts = ["bin/" + i for i in os.listdir("bin")]

setup(
    name="radiopadre",
    version=__version__,
    install_requires=install_requires,
    extras_require={"casacore" : ["python-casacore"] },
    python_requires='>=3.6',
    author="Oleg Smirnov",
    author_email="osmirnov@gmail.com",
    description=("A data visualization framework for jupyter notebooks"),
    license="MIT",
    keywords="ipython notebook jupyter fits dataset resultset visualisation",
    url="http://github.com/ratt-ru/radiopadre",
    packages=['radiopadre', 'radiopadre_kernel', 'radiopadre_utils'],
    scripts=scripts,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
    ],
)
