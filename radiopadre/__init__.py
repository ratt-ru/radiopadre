import json

import nbformat
import astropy
import os
import pkg_resources
import radiopadre.notebook_utils
from IPython.display import display, HTML, Javascript

from radiopadre.notebook_utils import _notebook_save_hook
from radiopadre.notebook_utils import scrub_cell

import radiopadre.settings_manager

settings = radiopadre.settings_manager.RadiopadreSettingsManager()

from .file import data_file, FileBase
from .dirlist import DataDir, DirList
from .filelist import FileList
from .fitsfile import FITSFile
from .imagefile import ImageFile
from .render import render_table, render_preamble, render_refresh_button, render_status_message, render_url, render_title

try:
    __version__ = pkg_resources.require("radiopadre")[0].version
except pkg_resources.DistributionNotFound:
    __version__ = "development"

## various notebook-related init
astropy.log.setLevel('ERROR')

ROOTDIR = os.getcwd()

def get_cache_dir(path, subdir=None):
    """Creates directory .radiopadre/subdir in directory of object given by path, and returns path to it.
    If write permissions not available, returns None
    """
    basedir = os.path.dirname(path)
    padre = os.path.join(basedir, ".radiopadre")
    if not os.path.exists(padre):
        if not os.access(basedir, os.W_OK):
            return None
        os.mkdir(padre)
    if not os.access(padre, os.W_OK):
        return None
    if not subdir:
        return padre if os.access(padre, os.W_OK) else None
    cache = os.path.join(padre, subdir)
    if not os.path.exists(cache):
        os.mkdir(cache)
    return cache if os.access(cache, os.W_OK) else None

def _init_js_side():
    """Checks that Javascript components of radiopadre are initialized"""
    try:
        get_ipython
    except:
        return None
    get_ipython().magic("matplotlib inline")
    # load radiopadre/js/init.js and init controls
    #initjs = os.path.join(os.path.dirname(__file__), "html", "init-radiopadre-components.js")
    #display(Javascript(open(initjs).read()))
    display(Javascript("document.radiopadre.register_user('%s')" % os.environ['USER']))
    # init JS9 components
    #import js9
    #display(Javascript(js9.get_init_js()))

def protect(author=None):
    """Makes current notebook protected with the given author name. Protected notebooks won't be saved
    unless the user matches the author."""
    author = author or os.environ['USER']
    display(Javascript("document.radiopadre.protect('%s')" % author))
    display(HTML(render_status_message("""This notebook is now protected, author is "%s".
        All other users will have to treat this notebook as read-only.""" % author)))


def unprotect():
    """Makes current notebook unprotected."""
    display(Javascript("document.radiopadre.unprotect()"))
    display(HTML(render_status_message("""This notebook is now unprotected.
        All users can treat it as read-write.""")))


def lsd(pattern=None, *args, **kw):
    """Creates a DirList from '.' non-recursively, optionally applying a pattern.

    Args:
        pattern: if specified, a wildcard pattern
    """
    kw['recursive'] = False
    dl = DirList(*args, **kw)
    return dl(pattern) if pattern else dl


def lsdr(pattern=None, *args, **kw):
    """Creates a DirList from '.' recursively, optionally applying a pattern.

    Args:
        pattern: if specified, a wildcard pattern
    """
    kw['recursive'] = True
    dl = DirList(*args, **kw)
    return dl(pattern) if pattern else dl


def latest(*args):
    """Creates a DirList from '.' recursively, optionally applying a pattern.

    Args:
        pattern (str):  if specified, a wildcard pattern
        num (int):      use 2 for second-latest, 3 for third-latest, etc.
    """
    args = dict([(type(arg), arg) for arg in args])
    dl = lsd(pattern=args.get(str), sort='txn')
    if not dl:
        raise (IOError, "no subdirectories here")
    return dl[-args.get(int, -1)].lsr()


def copy_current_notebook(oldpath, newpath, cell=0, copy_dirs='dirs', copy_root='root'):
    # read notebook data
    data = open(oldpath).read()
    version = json.loads(data)['nbformat']
    nbdata = nbformat.reads(data, version)
    nbdata.keys()
    # convert to current format
    current_version = nbformat.current_nbformat
    nbdata = nbformat.convert(nbdata, current_version)
    current_format = getattr(nbformat, 'v' + str(current_version))
    # accommodate worksheets, if available 
    if hasattr(nbdata, 'worksheets'):
        raise (RuntimeError, "copy_current_notebook: not compatible with worksheets")
    metadata = nbdata['metadata']
    cells = nbdata['cells']
    # strip out all cells up to and including indicated one
    del cells[:cell + 1]
    # scrub cell output
    for c in cells:
        scrub_cell(c)
    # insert boilerplate code
    code = "import radiopadre\n" + \
           "%s = radiopadre.DirList('.')" % copy_dirs
    if copy_root:
        code += "\n%s = %s[0]" % (copy_root, copy_dirs)
    code += "\n%s.show()" % copy_dirs
    # insert output
    output = current_format.new_output("display_data", data={
        "text/html": ["<b style='color: red'>Please select Cell|Run all from the menu to render this notebook.</b>"]
    })
    cells.insert(0, current_format.new_code_cell(code, outputs=[output]))
    # insert markdown
    cells.insert(0, current_format.new_markdown_cell("""# %s\nThis
                radiopadre notebook was automatically generated from ``%s`` 
                using the 'copy notebook' feature. Please select "Cell|Run all"
                from the menu to render this notebook.
                """ % (newpath, oldpath),
                                                     ))
    # cleanup metadata
    metadata['radiopadre_notebook_protect'] = 0
    metadata['radiopadre_notebook_scrub'] = 0
    if 'signature' in metadata:
        metadata['signature'] = ""
    # save
    nbformat.write(nbdata, open(newpath, 'w'), version)
    return newpath
