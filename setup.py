import os
import subprocess
from setuptools import setup
from setuptools.command.install import install

__version__ = "1.0-pre3"

with open("requirements.txt") as stdr:
    install_requires = stdr.readlines()

scripts = ["bin/" + i for i in os.listdir("bin")]

class SetupVenvCommand(install):
    """A custom command to setup radiopadre virtual environment"""

    def run(self):
        """Run command"""
        install.run(self)
        command = ['./bin/setup-radiopadre-virtualenv']
        subprocess.check_call(command)

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
    scripts=scripts,
    packages=['radiopadre', 'radiopadre_kernel', 'radiopadre_utils'],
    cmdclass={
              'install': SetupVenvCommand,
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.6",
    ],
)
