import json

import nbformat
import astropy
import os
import pkg_resources
import traceback
from IPython.display import display, HTML, Javascript

from radiopadre_utils.notebook_utils import scrub_cell

import radiopadre.settings_manager
from radiopadre.render import render_error, show_exception

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
from .render import render_table, render_preamble, render_refresh_button, render_status_message, rich_string, render_url, render_title

try:
    __version__ = pkg_resources.require("radiopadre")[0].version
except pkg_resources.DistributionNotFound:
    __version__ = "development"

## various notebook-related init
astropy.log.setLevel('ERROR')

# NONE OF THE DIR NAMES ABOVE SHALL HAVE A TRALING SLASH!!!

def display_setup():
    data = [ ("cwd", os.getcwd()) ]
    for varname in """ROOTDIR ABSROOTDIR DISPLAY_ROOTDIR SHADOW_HOME 
                    SERVER_BASEDIR SHADOW_ROOTDIR URLBASE SHADOW_URLBASE CACHE_URLBASE""".split():
        data.append((varname, globals()[varname]))

    display(HTML(render_table(data, ["", ""], numbering=False)))

def _strip_slash(path):
    return path if path == "/" or path is None else path.rstrip("/")

def _is_subdir(subdir, parent):
    return subdir == parent or subdir.startswith(parent+"/")

def _make_symlink(source, link_name):
    try:
        if os.path.lexists(link_name):
            if os.path.samefile(os.path.realpath(link_name), source):
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
ROOTDIR = None          # relative path to "root" diretcory (normally .)
DISPLAY_ROOTDIR = None  # what the root directory should be rewritten as, for display purposes
SHADOW_HOME = None      # base dir for the shadow directory tree
SERVER_BASEDIR = None   # base dir where the Jupyter server is running, e.g. /home/user/path
SHADOW_ROOTDIR = None   # "root" directory in shadow tree, e.g. ~/.radiopadre/home/user/path/to
SHADOW_URLBASE = None   # base URL for HTTP server serving shadow tree (e.g. http://localhost:port/xxx)
URLBASE = None          # base URL for accessing files through Jupyter (e.g. /files/to)
SESSION_ID = None       # session ID, used to access cache server etc.
CACHE_URLBASE = None    # base URL for cache, e.g. http://localhost:port/{SESSION_ID}/home/user/path

def init(rootdir=None, verbose=True):
    global ABSROOTDIR
    global ROOTDIR
    global DISPLAY_ROOTDIR
    global SHADOW_HOME
    global SERVER_BASEDIR
    global SHADOW_ROOTDIR
    global SHADOW_URLBASE
    global URLBASE
    global SESSION_ID
    global CACHE_URLBASE

    rootdir =_strip_slash(os.path.abspath(rootdir or '.'))
    if ABSROOTDIR is not None and os.path.samefile(rootdir, ABSROOTDIR):
        return

    ABSROOTDIR      = rootdir
    SHADOW_HOME     = _strip_slash(os.path.abspath(os.environ.get('RADIOPADRE_SHADOW_HOME') or os.path.expanduser("~/.radiopadre")))
    SERVER_BASEDIR  = _strip_slash(os.path.abspath(os.environ.get('RADIOPADRE_SERVER_BASEDIR') or os.getcwd()))
    DISPLAY_ROOTDIR = _strip_slash(os.environ.get("RADIOPADRE_DISPLAY_ROOT") or '.')
    SHADOW_URLBASE  = _strip_slash(os.environ.get('RADIOPADRE_SHADOW_URLBASE'))
    SESSION_ID      = os.environ.get('RADIOPADRE_SESSION_ID')

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
        # Otherwise it'd better have been /home/alien/path/to to begin with!
        if not _is_subdir(ABSROOTDIR, unshadowed_server_base):
            raise show_exception("""
                The requested directory {} is not under {}.
                This is probably a bug! """.format(ABSROOTDIR, unshadowed_server_base))
        # Since Jupyter is running under ~/.radiopadre/home/alien/path, we can serve alien's files from
        # /home/alien/path/to as /files/to/.content
        subdir = SHADOW_ROOTDIR[len(SERVER_BASEDIR):]   # this becomes "/to" (or "" if paths are the same)
        URLBASE = "/files{}/.radiopadre.content".format(subdir)
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
        URLBASE = "/files" + subdir

    os.chdir(ABSROOTDIR)
    ROOTDIR = '.'

    # check if we have a URL to access the shadow tree directly. If not, we can use "limp-home" mode
    # (i.e. the Jupyter server itself to access cache), but some things won't work
    if SHADOW_URLBASE is None:
        if not os.access(ABSROOTDIR, os.W_OK):
            raise show_exception("""
                The notebook is in a non-writeable directory {ABSROOTDIR}. Radiopadre needs a shadow HTTP
                server to deal with this situation, but this doesn't appear to have been set up.
                This is probably because you've attempted to load a radiopadre notebook from a 
                vanilla Jupyter session. Please use the run-radiopadre script to start Jupyter instead 
                (or report a bug if that's what you're already doing!)""".format(**globals()))
        else:
            display(HTML(render_error("""Warning: the radiopadre shadow HTTP server does not appear to be set up properly.
                                      Running with restricted functionality (e.g. JS9 will not work).""")))
        CACHE_URLBASE = "/files" + subdir
    else:
        CACHE_URLBASE = SHADOW_URLBASE + ABSROOTDIR

    import radiopadre.js9
    radiopadre.js9.init_js9()

    ## Uncomment the line below when debugging paths setup
    if verbose:
        display_setup()

def get_cache_dir(path, subdir=None):
    """
    Creates directory for caching radiopadre stuff associated with the given file.

    Returns tuple of (real_path, url_path). The former is the real filesystem location of the directory.
    The latter is the URL to this directory.
    """
    if ABSROOTDIR is None:
        raise RuntimeError("radiopadre.init() must be called first")
    basedir = _strip_slash(os.path.abspath(os.path.dirname(path)))
    if not _is_subdir(basedir, ABSROOTDIR):
        raise RuntimeError("Trying to access {}, which is outside the {} hierarchy".format(basedir, ABSROOTDIR))
    # if in a subdirectory off the root, this becomes the relative path to it, else ""
    reldir = basedir[len(ABSROOTDIR):]
    cacheurl = CACHE_URLBASE + reldir + "/.radiopadre"
    cachedir = None

    # if we can write to the basedir, make a .radiopadre dir within, and make a symlink to it in the shadow tree.
    if os.access(basedir, os.W_OK):
        cachedir = basedir + "/.radiopadre"
        if not os.path.exists(cachedir):
            os.mkdir(cachedir)
        if os.access(cachedir, os.W_OK):
            shadow_dir = SHADOW_HOME + basedir
            if not os.path.exists(shadow_dir):
                os.system("mkdir -p {}".format(shadow_dir))
            _make_symlink(cachedir, shadow_dir + "/.radiopadre")
        else:
            cachedir = None

    # if cachedir remains None, we weren't able to make a writeable one in the main tree -- use shadow tree
    # if this fails, we're stuck, so may as well bomb out
    if cachedir is None:
        if not SHADOW_URLBASE:
            raise RuntimeError("Trying to view non-writeable directory, but access to the shadow tree is not set up. This is a bug.")
        cachedir = SHADOW_HOME + basedir + "/.radiopadre"
        if not os.path.exists(cachedir):
            os.mkdir(cachedir)

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

def _ls(sort='dxnt', recursive=False, *args):
    """Creates a DirList from the given arguments (name and/or patterns)

    Args:
        pattern: if specified, a wildcard pattern
    """
    basedir = None
    include = []

    for arg in args:
        # arguments starting with "-" are sort keys. 'R' foreces recursive mode
        if arg[0] == '-':
            sort = arg[1:]
            if 'R' in sort:
                recursive = True
        # arguments with *? are include patterns. A slash forces recursive mode
        elif '*' in arg or '?' in arg:
            include.append(arg)
            if '/' in arg:
                recursive = True
        # other arguments is a directory name
        else:
            if basedir is None:
                if not os.path.isdir(arg):
                    return render_error("No such directory: {}".format(arg))
                basedir = arg
            else:
                return render_error("Directory specified more than once: {} and {}".format(basedir, arg))
    basedir = basedir or '.'
    title = rich_string(os.path.abspath(basedir) if basedir == '.' else basedir, bold=True)
    if recursive:
        title.prepend("[R]")

    return DataDir(basedir or '.', include=include or None, recursive=recursive, title=title, sort=sort)

def ls(*args):
    """
    Creates a DirList from '.' non-recursively, optionally applying a file selection pattern.
    Sorts in default order (directory, extension, name, mtime)
    """
    return _ls('dxnt', False, *args)

def lsR(*args):
    """
    Creates a DirList from '.' recursively, optionally applying a file selection pattern.
    Sorts in default order (directory, extension, name, mtime)
    """
    return _ls('dxnt', True, *args)


def lst(*args):
    """
    Creates a DirList from '.' non-recursively, optionally applying a file selection pattern.
    Sorts in time order (directory, mtime, extension, name)
    """
    return _ls('dtxn', False, *args)

def lsrt(*args):
    """
    Creates a DirList from '.' non-recursively, optionally applying a file selection pattern.
    Sorts in reverse time order (directory, -mtime, extension, name)
    """
    return _ls('rtdxn', False, *args)


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
    _init_js_side()

