## rsync -uvzR
import radiopadre
import subprocess, os.path
import ipynbname
from typing import Optional

from radiopadre.render import TransientMessage
from radiopadre.textfile import NumberedLineList


def capture_output(output, title=None):
    """Converts process output into a NumberedLineList object

    Args:
        output (bytes|str|None): process output
        title (str, optional): Sets title of line list. Defaults to None.

    Returns:
        NumberedLineList: encapsulated output
    """
    from radiopadre.textfile import NumberedLineList

    if output is None:
        lines = []
    else:
        if type(output) is bytes:
            output = output.decode('utf-8')
        lines = output.rstrip().split("\n")
    return NumberedLineList(enumerate(lines), title=title)


def render_notebook(nbname: Optional[str] = None):
    """Renders notebook to embedded HTNML.

    Args:
        nbname (Optional[str], optional): Filename of notebook. Auto-detected by default.
    """
    if radiopadre.NBCONVERT:
        return NumberedLineList([], title="will not render notebook when already in convert mode")

    nbname = nbname or ipynbname.path()
    # print(nbdir, nbname)
    
    # run-radiopadre needs to be told to set up an environment fresh, so we clear out certain variables from the venv
    env = os.environ.copy()
    env.pop('RADIOPADRE_SERVER_BASEDIR')
    env.pop('RADIOPADRE_HTTPSERVER_PID')
    cmd = f"run-radiopadre -V --nbconvert {nbname}"

#    cmd = "pwd"
    msg = TransientMessage("Rendering notebook to HTML, please wait...", timeout=30)
    try:    
        output = subprocess.check_output(cmd, shell=True, env=env, stderr=subprocess.STDOUT)
        output += f"Successfully rendered {nbname}".encode()
    except subprocess.CalledProcessError as exc:
        output = exc.output + exc.stderr + f"Conversion exited with error code {exc.returncode}".encode()
    del msg
    
    return capture_output(output, title=cmd)

