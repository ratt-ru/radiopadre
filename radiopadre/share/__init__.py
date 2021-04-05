import iglesia
import ipynbname
import radiovangelize.push
from radiovangelize.render import capture_output
from radiovangelize.render import render_notebook as render


def get_push_config():
    return radiovangelize.push.get_push_config(iglesia.ABSROOTDIR)


def push(**kw):
    import radiopadre
    from radiopadre.render import TransientMessage

    if radiopadre.NBCONVERT:
        return None

    name = ipynbname.path()

    msg = TransientMessage(f"Pushing notebook {name}, please wait...", timeout=30)
    try:    
        output = radiovangelize.push.push_notebook(name, capture_output=True, **kw)
    finally:
        del msg

    return capture_output(output, f"Pushing {name}")

