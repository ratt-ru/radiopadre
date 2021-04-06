import io, logging, os
from typing import Union
import iglesia
import ipynbname
import radiovangelize.push
import radiopadre
from radiopadre.render import TransientMessage

from radiovangelize.render import render_notebook as render


def _convert_to_linelist(output: Union[bytes, str], title: str=None):
    """Converts bytes or str into a NumberedLineList object

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


def _init_stream_handler(verbose=False):
    output_stream = io.StringIO()
    handler = logging.StreamHandler(output_stream)
    handler.setFormatter(logging.Formatter("{levelname}: {message}", style="{"))
    handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    iglesia.logger.logger.addHandler(handler) 

    return output_stream, handler


def get_push_config():
    return radiovangelize.push.get_push_config(iglesia.ABSROOTDIR)


def _call_vangelize_method(method, message, title, args):
    output_stream, handler = _init_stream_handler() 
    msg = TransientMessage(message, timeout=30)
  
    try:
        method(output_stream=output_stream, **args)
    finally:
        iglesia.logger.logger.removeHandler(handler) 
        del msg

    return _convert_to_linelist(output_stream.getvalue(), title)


def render(**kw):
    if radiopadre.NBCONVERT:
        return None

    # run-radiopadre needs to be told to set up an environment fresh, so we clear out certain variables from the venv
    args = dict(path=ipynbname.path(), **kw)

    return _call_vangelize_method(radiovangelize.render.render_notebook,
                    message=f"Rendering notebook to HTML, please wait...",
                    title=f"Rendering notebook ",
                    args=args)



def push(**kw):
    if radiopadre.NBCONVERT:
        return None

    path = ipynbname.path()
    args = dict(path=path, **kw)

    return _call_vangelize_method(radiovangelize.push.push_notebook,
                    message=f"Pushing notebook {path}, please wait...",
                    title=f"Pushing {path}",
                    args=args)


def list(**kw):
    if radiopadre.NBCONVERT:
        return None

    return _call_vangelize_method(radiovangelize.push.list_remotes,
                    message=f"Getting listing, please wait...",
                    title=f"List of remote contents",
                    args=kw)

