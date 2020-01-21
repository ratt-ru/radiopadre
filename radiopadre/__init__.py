import json

import nbformat
import astropy
import os
import pkg_resources
import traceback
import itertools
from collections import OrderedDict

from IPython.display import display, HTML, Javascript

from radiopadre_utils.notebook_utils import scrub_cell

from radiopadre import settings_manager
from radiopadre.render import render_error, show_exception, TransientMessage
from radiopadre.table import tabulate

_startup_warnings = []

def add_startup_warning(message):
    global _startup_warnings
    _startup_warnings.append(message)

# init settings
settings = settings_manager.RadiopadreSettingsManager()

try:
    import casacore.tables as casacore_tables
except Exception as exc:
    casacore_tables = None
    add_startup_warning("""Warning: casacore.tables failed to import ({}). Table browsing functionality will 
        not be available in this notebook. You probably want to install casacore-dev and python-casacore on this 
        system ({}), then reinstall the radiopadre environment.
        """.format(exc, os.environ['HOSTNAME']))


from .file import autodetect_file_type
from .datadir import DataDir, ls, lsR, lst, lsrt
from .filelist import FileList
from .fitsfile import FITSFile
from .imagefile import ImageFile
from .casatable import CasaTable
from .render import render_table, render_preamble, render_refresh_button, render_status_message, rich_string, render_url, render_title

try:
    __version__ = pkg_resources.require("radiopadre")[0].version
except pkg_resources.DistributionNotFound:
    __version__ = "development"

## various notebook-related init
astropy.log.setLevel('ERROR')

# NONE OF THE DIR NAMES ABOVE SHALL HAVE A TRALING SLASH!!!

def _strip_slash(path):
    return path if path == "/" or path is None else path.rstrip("/")

def _is_subdir(subdir, parent):
    return subdir == parent or subdir.startswith(parent+"/")

def _make_symlink(source, link_name):
    try:
        if os.path.lexists(link_name):
            if os.path.exists(link_name) and os.path.samefile(link_name, source):
                return
            else:
                os.unlink(link_name)
        os.symlink(source, link_name)
    except Exception:
        traceback.print_exc()
        show_exception("""
            Error creating {} symlink. This is a permissions problem, or a bug!""".format(link_name))

# NONE OF THE DIR NAMES BELOW SHALL HAVE A TRALING SLASH!!!
# Use _strip_slash() when in doubt.

ABSROOTDIR = None       # absolute path to "root" directory, e.g. /home/user/path/to
ROOTDIR = None          # relative path to "root" directory (normally .)
DISPLAY_ROOTDIR = None  # what the root directory should be rewritten as, for display purposes
SHADOW_HOME = None      # base dir for the shadow directory tree

SERVER_BASEDIR = None   # dir where the Jupyter server is running, e.g. /home/user/path (or ~/.radiopadre/home/user/path)
SHADOW_BASEDIR = None   # shadow equivalent of above, i.e. ~/.radiopadre/home/user/path in both cases
SHADOW_ROOTDIR = None   # "root" directory in shadow tree, e.g. ~/.radiopadre/home/user/path/to

SHADOW_URL_PREFIX = None   # URL prefix for HTTP server serving shadow tree (e.g. http://localhost:port/{SESSION_ID})
FILE_URL_ROOT = None       # root URL for accessing files through Jupyter (e.g. /files/to)
NOTEBOOK_URL_ROOT = None   # root URL for accessing notebooks through Jupyter (e.g. /notebooks/to)
CACHE_URL_BASE = None      # base URL for cache, e.g. http://localhost:port/{SESSION_ID}/home/user/path
CACHE_URL_ROOT = None      # URL for cache of root dir, e.g. http://localhost:port/{SESSION_ID}/home/user/path/to

def display_setup():
    data = [ ("cwd", os.getcwd()) ]
    for varname in """ROOTDIR ABSROOTDIR DISPLAY_ROOTDIR SHADOW_HOME 
                      SERVER_BASEDIR SHADOW_BASEDIR SHADOW_ROOTDIR 
                      SHADOW_URL_PREFIX FILE_URL_ROOT CACHE_URL_BASE CACHE_URL_ROOT""".split():
        data.append((varname, globals()[varname]))

    display(HTML(render_table(data, ["", ""], numbering=False)))



def init(rootdir=None, verbose=True):
    global ABSROOTDIR
    global ROOTDIR
    global DISPLAY_ROOTDIR
    global SHADOW_HOME
    global SERVER_BASEDIR
    global SHADOW_BASEDIR
    global SHADOW_ROOTDIR

    global SHADOW_URL_PREFIX
    global FILE_URL_ROOT
    global NOTEBOOK_URL_ROOT
    global SESSION_ID
    global CACHE_URL_ROOT
    global CACHE_URL_BASE

    rootdir =_strip_slash(os.path.abspath(rootdir or '.'))
    if ABSROOTDIR is not None and os.path.samefile(rootdir, ABSROOTDIR):
        return

    ABSROOTDIR        = rootdir
    SHADOW_HOME       = _strip_slash(os.path.abspath(os.environ.get('RADIOPADRE_SHADOW_HOME') or os.path.expanduser("~/.radiopadre")))
    SERVER_BASEDIR    = _strip_slash(os.path.abspath(os.environ.get('RADIOPADRE_SERVER_BASEDIR') or os.getcwd()))
    DISPLAY_ROOTDIR   = _strip_slash(os.environ.get("RADIOPADRE_DISPLAY_ROOT") or '.')
    SHADOW_URL_PREFIX = _strip_slash(os.environ.get('RADIOPADRE_SHADOW_URLBASE'))

    ALIEN_MODE = _is_subdir(SERVER_BASEDIR, SHADOW_HOME)

    # if our rootdir is ~/.radiopadre/home/alien/path/to, then change it to /home/alien/path/to
    if _is_subdir(ABSROOTDIR, SHADOW_HOME):
        ABSROOTDIR = ABSROOTDIR[len(SHADOW_HOME):]
    # and this will be ~/.radiopadre/home/alien/path/to
    SHADOW_ROOTDIR = SHADOW_HOME + ABSROOTDIR

    # setup for alien mode. Browsing /home/alien/path/to, where "alien" is a different user
    if ALIEN_MODE:
        # for a Jupyter basedir of ~/.radiopadre/home/alien/path, this becomes /home/alien/path
        unshadowed_server_base = SERVER_BASEDIR[len(SHADOW_HOME):]
        SHADOW_BASEDIR = SERVER_BASEDIR
        # Otherwise it'd better have been /home/alien/path/to to begin with!
        if not _is_subdir(ABSROOTDIR, unshadowed_server_base):
            raise show_exception("""
                The requested directory {} is not under {}.
                This is probably a bug! """.format(ABSROOTDIR, unshadowed_server_base))
        # Since Jupyter is running under ~/.radiopadre/home/alien/path, we can serve alien's files from
        # /home/alien/path/to as /files/to/.content
        subdir = SHADOW_ROOTDIR[len(SERVER_BASEDIR):]   # this becomes "/to" (or "" if paths are the same)
        FILE_URL_ROOT = "/files{}/.radiopadre.content".format(subdir)
        NOTEBOOK_URL_ROOT = "/notebooks{}/.radiopadre.content".format(subdir)
        # but do make sure that the .content symlink is in place!
        _make_symlink(ABSROOTDIR, SHADOW_ROOTDIR + "/.radiopadre.content")
    # else running in native mode
    else:
        if not _is_subdir(ABSROOTDIR, SERVER_BASEDIR):
            raise show_exception("""
                The requested directory {ABSROOTDIR} is not under {SERVER_BASEDIR}.
                This is probably a bug! """.format(**globals()))
        # for a server dir of /home/user/path, and an ABSROOTDIR of /home/oms/path/to, get the subdir
        subdir = ABSROOTDIR[len(SERVER_BASEDIR):]   # this becomes "/to" (or "" if paths are the same)
        FILE_URL_ROOT = "/files" + subdir
        NOTEBOOK_URL_ROOT = "/notebooks" + subdir
        SHADOW_BASEDIR = SHADOW_HOME + SERVER_BASEDIR

    os.chdir(ABSROOTDIR)
    ROOTDIR = '.'

    # check if we have a URL to access the shadow tree directly. If not, we can use "limp-home" mode
    # (i.e. the Jupyter server itself to access cache), but some things won't work
    if SHADOW_URL_PREFIX is None:
        if not os.access(ABSROOTDIR, os.W_OK):
            raise show_exception("""
                The notebook is in a non-writeable directory {ABSROOTDIR}. Radiopadre needs a shadow HTTP
                server to deal with this situation, but this doesn't appear to have been set up.
                This is probably because you've attempted to load a radiopadre notebook from a 
                vanilla Jupyter session. Please use the run-radiopadre-server script to start Jupyter instead 
                (or report a bug if that's what you're already doing!)""".format(**globals()))
        else:
            display(HTML(render_error("""Warning: the radiopadre shadow HTTP server does not appear to be set up properly.
                                      Running with restricted functionality (e.g. JS9 will not work).""")))
        CACHE_URL_BASE = "/files"
        CACHE_URL_ROOT = "/files" + subdir
    else:
        CACHE_URL_ROOT = SHADOW_URL_PREFIX + ABSROOTDIR
        CACHE_URL_BASE = CACHE_URL_ROOT[:-len(subdir)] if subdir else CACHE_URL_ROOT

    ## Uncomment the line below when debugging paths setup
    if verbose:
        display_setup()

def get_cache_dir(path, subdir=None):
    """
    Creates directory for caching radiopadre stuff associated with the given file.

    Returns tuple of (real_path, url_path). The former is the (shadow) filesystem location of the directory.
    The latter is the URL to this directory.
    """
    if ABSROOTDIR is None:
        raise RuntimeError("radiopadre.init() must be called first")
    basedir = _strip_slash(os.path.abspath(os.path.dirname(path)))
    if _is_subdir(basedir, ABSROOTDIR):
        # if in a subdirectory off the root, this becomes the relative path to it, else ""
        reldir = basedir[len(ABSROOTDIR):]
    elif _is_subdir(basedir, SHADOW_HOME+ABSROOTDIR):
        reldir = basedir[len(SHADOW_HOME)+len(ABSROOTDIR):]
    else:
        raise RuntimeError("Trying to access {}, which is outside the {} hierarchy".format(basedir, ABSROOTDIR))
    cacheurl = CACHE_URL_ROOT + reldir + "/.radiopadre"
    shadowdir = SHADOW_HOME + basedir
    cachedir = None

    # if we can write to the basedir, make a .radiopadre dir within, and make a symlink to it in the shadow tree.
    if os.access(basedir, os.W_OK):
        cachedir = basedir + "/.radiopadre"
        if not os.path.exists(cachedir):
            os.mkdir(cachedir)
        if os.access(cachedir, os.W_OK):
            if not os.path.exists(shadowdir):
                os.system("mkdir -p {}".format(shadowdir))
            shadowdir += "/.radiopadre"
            _make_symlink(cachedir, shadowdir)
            cachedir = shadowdir
        else:
            cachedir = None

    # if cachedir remains None, we weren't able to make a writeable one in the main tree -- use shadow tree
    # if this fails, we're stuck, so may as well bomb out
    if cachedir is None:
        if not SHADOW_URL_PREFIX:
            raise RuntimeError("Trying to view non-writeable directory, but access to the shadow tree is not set up. This is a bug.")
        cachedir = shadowdir + "/.radiopadre"
        if not os.path.exists(cachedir):
            os.system("mkdir -p {}".format(cachedir))

    if not os.access(cachedir, os.W_OK):
        raise RuntimeError("Cache directory {} not user-writeable. Try removing it?".format(cachedir))

    # make a cache subdir, if so required
    if subdir:
        cacheurl += "/" + subdir
        cachedir += "/" + subdir
        if not os.path.exists(cachedir):
            os.mkdir(cachedir)

    return cachedir, cacheurl


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
        console.log("reset display, width is", window.innerWidth, window.innerHeight);
        Jupyter.notebook.kernel.execute(`print "executing reset"; import radiopadre; radiopadre.set_window_sizes(
                                                ${width}, 
                                                ${window.innerWidth}, ${window.innerHeight})`);
    """

    def reset():
        display(Javascript(reset_code))

    settings.display.reset = reset, settings_manager.DocString("call this to reset sizes after e.g. a browser resize")

    global _startup_warnings
    warns = "\n".join([render_status_message(msg, bgcolor='yellow') for msg in _startup_warnings])

    import radiopadre.js9

    html = """{}
            <script type='text/javascript'>
            document.radiopadre.register_user('{}');
            {}
            </script>
         """.format(warns, os.environ['USER'], reset_code)

    styles_file = os.path.join(os.path.dirname(__file__), "../html/radiopadre.css")

    html += """<style>
        {}
    </style>""".format(open(styles_file).read())

    # <style>
    #     .container {{ width:100% !important; }}
    # </style>

    # print "executing reset code"

    display(HTML(html))


def set_window_sizes(cell_width,window_width,window_height):
    settings.display.cell_width, settings.display.window_width, settings.display.window_height = cell_width, window_width, window_height


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

if ROOTDIR is None:
    init(os.getcwd(), False)
    import radiopadre.js9
    radiopadre.js9.init_js9()
    _init_js_side()


