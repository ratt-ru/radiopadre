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

_startup_warnings = []

def add_startup_warning(message):
    global _startup_warnings
    _startup_warnings.append(message)

# init settings
settings = radiopadre.settings_manager.RadiopadreSettingsManager()

try:
    import casacore.tables as casacore_tables
except Exception,exc:
    casacore_tables = None
    add_startup_warning("""Warning: casacore.tables failed to import ({}). Table browsing functionality will 
        not be available in this notebook. You probably want to install casacore-dev and python-casacore on this 
        system ({}), then reinstall the radiopadre environment.
        """.format(exc, os.environ['HOSTNAME']))


from .datadir import DataDir
from .filelist import FileList
from .fitsfile import FITSFile
from .imagefile import ImageFile
from .casatable import CasaTable
from .render import render_table, render_preamble, render_refresh_button, render_status_message, render_url, render_title

try:
    __version__ = pkg_resources.require("radiopadre")[0].version
except pkg_resources.DistributionNotFound:
    __version__ = "development"

## various notebook-related init
astropy.log.setLevel('ERROR')

ROOTDIR = os.environ.get('RADIOPADRE_ROOTDIR') or os.getcwd()

WORKDIR = os.environ.get('RADIOPADRE_WORKDIR') or ".radiopadre"
WORKDIR_REDIRECT = os.environ.get('RADIOPADRE_WORKDIR_REDIRECT') or None

# We have two running scenarios:
#
# 1. No redirect. Running radiopadre in a directory owned (and writable) by the user, say /path/to/directory. Then
#
#       * jupyter server is started and runs in /path/to/directory
#       * radiopadre cache and support files live in WORKDIR=/path/to/directory/.radiopadre
#       * kernel runs in /path/to/directory
#
# 2. Redirect mode. Running radiopadre to look at files owned by someone else. Then a local "redirect" work directory
#    is created under ~/.radiopadre, and:
#
#       * jupyter server is started and runs in ~/.radiopadre/path/to/directory
#       * radiopadre cache and support files live in WORKDIR=~/.radiopadre/path/to/directory/.radiopadre
#       * kernel runs in /path/to/directory
#
if WORKDIR_REDIRECT:
    os.chdir(ROOTDIR)
    add_startup_warning("Directories: current {}, workdir {}".format(ROOTDIR, WORKDIR_REDIRECT))

def get_cache_dir(path, subdir=None):
    """
    Creates directory for caching radiopadre stuff associated with the given file.
    For an file given by path/to/directory/filename, the cache directory is either
        path/to/directory/.radiopadre[/subdir]
        ~/.radiopadre/path/to/directory/.radiopadre[/subdir]
    ...depending on whether radiopadre used the current directory as the workdir (normally the case when you
    run radiopadre in your own files), or ~/.radiopadre (i.e. "workdir redirect" mode. normally the case when looking at
    others' files)

    Returns tuple of (real_path, url_path). The former is the real filesystem location of the directory.
    The latter is the URL to this directory. In workdir redirect mode, the two are different
    """
    basedir = os.path.dirname(path)
    if not os.path.abspath(basedir).startswith(os.path.abspath(ROOTDIR)):
        raise RuntimeError("Trying to make cache for directory {} that is outside the current hierarchy {}".format(
                            path, ROOTDIR))

    if WORKDIR_REDIRECT:
        padre = WORKDIR
        urlpath = ".radiopadre"
        if os.path.samefile(basedir, ROOTDIR):
            if not os.path.exists(padre):
                os.mkdir(padre)
        else:
            components = list(basedir.split("/"))
            components.append(".radiopadre")
            for comp in components:
                if not os.access(padre, os.W_OK):
                    raise RuntimeError("no write access to {}. Make sure you have the correct persmissions.".format(padre))
                padre = os.path.join(padre, comp)
                urlpath = os.path.join(urlpath, comp)
                if not os.path.exists(padre):
                    os.mkdir(padre)
    else:
        padre = urlpath = os.path.join(basedir, ".radiopadre")
        if os.path.exists(padre):
            if not os.access(padre, os.W_OK):
                raise RuntimeError("no write access to {}. Run radiopadre with --workdir-home.".format(padre))
        else:
            if not os.access(basedir, os.W_OK):
                raise RuntimeError("no write access to {}. Run radiopadre with --workdir-home.".format(basedir))
            os.mkdir(padre)

    if not subdir:
        return padre, urlpath

    cache = os.path.join(padre, subdir)
    urlpath = os.path.join(urlpath, subdir)
    if not os.path.exists(cache):
        os.mkdir(cache)

    return cache, urlpath


_init_js_side_done = None

def _init_js_side():
    """Checks that Javascript components of radiopadre are initialized, does various other init"""
    global _init_js_side_done
    if _init_js_side_done:
        return
    _init_js_side_done = True
    try:
        get_ipython
    except:
        return None
    get_ipython().magic("matplotlib inline")
    # load radiopadre/js/init.js and init controls
    #initjs = os.path.join(os.path.dirname(__file__), "html", "init-radiopadre-components.js")
    #display(Javascript(open(initjs).read()))

    reset_code = """
        var width = $(".rendered_html")[0].clientWidth;
        Jupyter.notebook.kernel.execute(`import radiopadre; radiopadre.set_window_sizes(
                                                ${width}, 
                                                ${window.innerWidth}, ${window.innerHeight})`);
    """

    def reset():
        display(Javascript(reset_code))
    settings.display.reset = reset, radiopadre.settings_manager.DocString("call this to reset sizes after e.g. a browser resize")

    global _startup_warnings
    warns = "\n".join([render_status_message(msg, bgcolor='yellow') for msg in _startup_warnings])


    display(HTML("""{}
                    <script type='text/javascript'>
                    document.radiopadre.register_user('{}');
                    {}
                    </script>
                 """.format(warns, os.environ['USER'], reset_code, __version__)))


def set_window_sizes(cell_width,window_width,window_height):
    settings.display.cell_width, settings.display.window_width, settings.display.window_height = cell_width, window_width, window_height

# call this once
_init_js_side()



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

def ls(pattern=None):
    """Creates a DirList from '.' non-recursively, optionally applying a pattern.

    Args:
        pattern: if specified, a wildcard pattern
    """
    dd = DataDir('.')
    return DataDir(pattern) if pattern else dd

def lst(pattern=None):
    """Creates a DirList from '.' non-recursively, optionally applying a pattern.

    Args:
        pattern: if specified, a wildcard pattern
    """
    dd = DataDir('.', sort="dtnx")
    return DataDir(pattern) if pattern else dd

def lsrt(pattern=None):
    """Creates a DirList from '.' non-recursively, optionally applying a pattern.

    Args:
        pattern: if specified, a wildcard pattern
    """
    dd = DataDir('.', sort="dtnxr")
    return DataDir(pattern) if pattern else dd



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
