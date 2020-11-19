import os
import subprocess
from setuptools import setup
from setuptools.command.install import install
from setuptools.command.develop import develop
from wheel.bdist_wheel import bdist_wheel

__version__ = "1.1.1"
build_root = os.path.dirname(__file__)

with open("requirements.txt") as stdr:
    install_requires = stdr.readlines()

scripts = ["bin/" + i for i in os.listdir("bin")]


class WheelSetupVenvCommand(bdist_wheel):
    """A custom wheel command to setup radiopadre virtual environment"""

    def run(self):
        """Run command"""
        pass

class InstallSetupVenvCommand(install):
    """A custom install command to setup radiopadre virtual environment"""

    def run(self):
        """Run command"""
        install.run(self)
        command = ['./bin/setup-radiopadre-virtualenv']
        subprocess.check_call(command)

class DevelopSetupVenvCommand(develop):
    """A custom develop command to setup radiopadre virtual environment"""

    def run(self):
        """Run command"""
        develop.run(self)
        command = ['./bin/setup-radiopadre-virtualenv', '--editable']
        subprocess.check_call(command)

def readme():
    """Get readme content for package long description"""
    with open(os.path.join(build_root, 'README.rst')) as f:
        return f.read()

setup(
    name="radiopadre",
    version=__version__,
    install_requires=install_requires,
    extras_require={"casacore" : ["python-casacore"] },
    python_requires='>=3.6',
    author="Oleg Smirnov",
    author_email="osmirnov@gmail.com",
    description=("A data visualization framework for jupyter notebooks"),
    long_description=readme(),
    license="MIT",
    keywords="ipython notebook jupyter fits dataset resultset visualisation",
    url="http://github.com/ratt-ru/radiopadre",
    scripts=scripts,
    packages=['radiopadre', 'radiopadre_kernel', 'radiopadre_kernel/js9', 'radiopadre_utils'],
    include_package_data=True,
    cmdclass={
              'install': InstallSetupVenvCommand,
              'develop': DevelopSetupVenvCommand,
              'bdist_wheel': WheelSetupVenvCommand,
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.6",
    ],
)

