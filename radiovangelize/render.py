import os.path
from iglesia import message, error

from .push import _run_command

def render_notebook(path: str, output_stream=None, **kw):
    """Renders notebook to embedded HNML.

    Args:
        path (str): Filename of notebook.
    """
    message(f"Rendering notebook {path}", color="GREEN")

    # run-radiopadre needs to be told to set up an environment fresh, so we clear out certain variables from the venv
    env = os.environ.copy()
    env.pop('RADIOPADRE_SERVER_BASEDIR', None)
    env.pop('RADIOPADRE_HTTPSERVER_PID', None)
    cmd = f"$run-radiopadre -V --nbconvert {path}"

    retcode = _run_command(cmd, output_stream=output_stream, env=env)

    if retcode:
        error(f"Rendering command exited with error code {retcode}")
    else:
        message(f"Notebook {path} successfully rendered", color="GREEN")

    return retcode
