## rsync -uvzR
from genericpath import exists
import iglesia
import radiopadre
import subprocess, os.path, traceback
from subprocess import PIPE, run
import click
from omegaconf import OmegaConf
from IPython.display import display, Javascript
import ipynbname
from dataclasses import dataclass
from typing import KeysView, Optional

from radiopadre.render import TransientMessage
from radiopadre.textfile import NumberedLineList

from iglesia import debug, message, warning, error

    

def render(nbname: Optional[str] = None):
    """Renders notebook to embedded HTNML.

    Args:
        nbname (Optional[str], optional): Filename of notebook. Auto-detected by default.
    """
    if radiopadre.NBCONVERT:
        return NumberedLineList([], title="will not render notebook when already in convert mode")

    nbpath = ipynbname.path()
    nbname = nbname or ipynbname.path()
    # print(nbdir, nbname)
    
    # run-radiopadre needs to be told to set up an environment fresh, so we clear out certain variables from the venv
    env = os.environ.copy()
    env.pop('RADIOPADRE_SERVER_BASEDIR')
    env.pop('RADIOPADRE_HTTPSERVER_PID')
    cmd = f"run-radiopadre -V --nbconvert {nbname or nbpath}"

#    cmd = "pwd"
    msg = TransientMessage("Rendering notebook to HTML, please wait...", timeout=30)
    try:    
        output = subprocess.check_output(cmd, shell=True, env=env, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as exc:
        output = exc.output + exc.stderr + f"Conversion exited with error code {exc.returncode}".encode()
    del msg
    return _capture_output(output, title=cmd)





# @click.group()
# @click.option('--backend', '-b', type=click.Choice(config.Backend._member_names_), 
#                 help="Backend to use (for containerization).")
# @click.version_option(str(stimela.__version__))
# @click.pass_context
# def cli(ctx, backend):
