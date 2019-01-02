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
from radiopadre.render import render_error

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

# We need to be able to look at both the user's own files, and other users' files. We also need to be able to run
# in a container. Consider also that:
#
#   1. Jupyter will only serve files under the directory it is started in (as /files/xxx)
#   2. The notebook should reside in the Jupyter starting directory, and be writeable by the user
#   3. We need a user-writeable cache directory to store thumbnails, JS9 launch scripts, etc. This must also reside
#      under the starting directory (to be servable by Jupyter). Ideally, we want to use .radiopadre inside
#      the actual subdirectory being viewed, but what if we don't own it?
#   4. If running in a container, the data directory might be mounted under some funny prefix (e.g. /mnt/data) that the user
#      doesn't recognize, this needs to be stripped out from pathnames
#
# Point (1) means we have to select a directory to be visualized in advance, and we can't go outside of that hierarchy.
# So let's say the user wants to be looking at /path/to/directory. We call this
#
#       DISPLAY_ROOTDIR = /path/to/directory
#
# Let's then assume the user is displaying the content of dir=/path/to/directory/foo/bar/.
#
# We have two ways of running radiopadre: native (or in a virtual environment), or in a container. The following
# scenarios then arise:
#
# I.   Native, /path/to/directory is user-writeable
#
#       Jupyter starting dir is /path/to/directory
#       ROOTDIR      = CWD = DISPLAY_ROOTDIR = /path/to/directory
#       CACHEBASE    = ROOTDIR/.radiopadre
#       URLBASE      =
#       CACHEURLBASE = .radiopadre
#       FAKEROOT     = False
#
# II.  Native, /path/to/directory is not user-writeable. We have to fake a directory in the user's $HOME.
#
#       Startup script will create a "fake" directory ~/.radiopadre/path/to/directory if needed, populate
#       it with a default notebook, and make a symlink "content" -> /path/to/directory
#       Jupyter starting dir is the fake dir, ~/.radiopadre/path/to/directory
#
#       ROOTDIR       = CWD = DISPLAY_ROOTDIR = /path/to/directory
#       CACHEBASE     = ~/.radiopadre/path/to/directory/cache
#       URLBASE       = content
#       CACHEURLBASE  = cache
#       FAKEROOT      = ~/.radiopadre/path/to/directory/
#
# III. Running in container, /path/to/directory is user-writeable, mounted under ROOT_MOUNT
#
#       DISPLAY_ROOTDIR = /path/to/directory
#       ROOTDIR      = CWD = ROOT_MOUNT
#       CACHEBASE    = ROOTDIR/.radiopadre
#       URLBASE      =
#       CACHEURLBASE = .radiopadre
#       FAKEROOT     = False
#
# IV.  Running in container, /path/to/directory is not user-writeable, mounted under ROOT_MOUNT.
#      User's directory will be mounted under HOME_MOUNT.
#      Startup script will create a "fake" directory HOME_MOUNT/.radiopadre/path/to/directory if needed, populate
#      it with a default notebook, and make a symlink "content" -> ROOT_MOUNT
#      Jupyter starting dir is the fake dir, HOME_MOUNT/.radiopadre/path/to/directory
#
#       DISPLAY_ROOTDIR = /path/to/directory
#       ROOTDIR      = CWD = ROOT_MOUNT
#       CACHEBASE    = HOME_MOUNT/.radiopadre/path/to/directory/cache
#       URLBASE      = content
#       CACHEURLBASE = cache
#       FAKEROOT     = HOME_MOUNT/.radiopadre/path/to/directory/
#
# Summarizing this into rules on variable setup:
#
#       DISPLAY_ROOTDIR = /path/to/directory        # always
#       ROOTDIR = CWD = DISPLAY_ROOTDIR             # in native mode
#                     = $RADIOPADRE_ROOT_MOUNT      # in container mode
#       HOME_MOUNT    = ~                           # in native mode
#                     = $RADIOPADRE_HOME_MOUNT      # in container mode
#       CACHEBASE     = ROOTDIR/.radiopadre         # if not FAKEROOT
#                       HOME_MOUNT/.radiopadre/path/to/directory/  # if FAKEROOT
#       URLBASE       =                             # if not FAKEROOT
#                     = content                     # if FAKEROOT
#       CACHEURLBASE  = .radiopadre                 # if not FAKEROOT
#                     = .radiopadre/content         # if FAKEROOT
#
# NONE OF THE DIR NAMES ABOVE SHALL HAVE A TRALING SLASH!!!
#
# Cache dir rules are as follows:
#       When looking at dir=/path/to/directory/foo/bar, if dir is user-writeable, use
#       /path/to/directory/foo/bar/.radiopadre for cache (URLBASE/foo/bar/.radiopadre is the URL), else
#       CACHEBASE/foo/bar (CACHEURLBASE/foo/bar is the URL)
#
# Rewriting rules are as follows:
#
#       1. Displayed paths always replace a leading ROOTDIR with DISPLAY_ROOTDIR
#       2. URLs for the native HTTP server (for e.g. JS9) replace /files with ""
#
# When starting up, we check if RADIOPADRE_ROOT_MOUNT is set, and assume container mode if so

_setup_done = False

def display_setup():
    data = [ ("cwd", os.getcwd()) ]
    for varname in "SERVER_BASEDIR", "DISPLAY_ROOTDIR", "ROOTDIR", "CACHEBASE", "URLBASE", "CACHEURLBASE":
        data.append((varname, globals()[varname]))

    display(HTML(render_table(data, ["", ""], numbering=False)))

def _strip_slash(path):
    return path if path == "/" or path is None else path.rstrip("/")

if not _setup_done:
    SERVER_BASEDIR = _strip_slash(os.environ.get('RADIOPADRE_SERVERDIR') or os.getcwd())

    RADIOPADRE_ROOT_MOUNT = _strip_slash(os.environ.get("RADIOPADRE_ROOT_MOUNT"))
    CONTAINER_MODE = bool(RADIOPADRE_ROOT_MOUNT)

    DISPLAY_ROOTDIR = _strip_slash(os.environ.get("RADIOPADRE_REALROOT") or os.getcwd())

    ROOTDIR = RADIOPADRE_ROOT_MOUNT or DISPLAY_ROOTDIR
    os.chdir(ROOTDIR)

    HOME_MOUNT = _strip_slash(os.environ.get("RADIOPADRE_HOME_MOUNT") or os.path.expanduser("~"))
    FAKEROOT = _strip_slash(os.environ.get("RADIOPADRE_FAKEROOT", "")) or None

    if not FAKEROOT:
        # if the webserver is running in a parent directory, adjust URL bases
        if not os.path.samefile(ROOTDIR, SERVER_BASEDIR):
            if not ROOTDIR.startswith(SERVER_BASEDIR+"/"):
                raise RuntimeError(
                    "Current directory {} is not a subdirectory of the notebook server base dir {}. This is a bug!".format(
                        ROOTDIR, SERVER_BASEDIR
                    ))
            URLBASE = ROOTDIR[len(SERVER_BASEDIR)+1:]
            CACHEURLBASE = os.path.join(URLBASE, ".radiopadre")
        else:
            URLBASE = ""
            CACHEURLBASE = ".radiopadre"
        CACHEBASE    = os.path.join(ROOTDIR, ".radiopadre")
    else:
        content = os.path.basename(FAKEROOT.rstrip("/"))
        URLBASE = content
        CACHEURLBASE = ".radiopadre"
        CACHEBASE = os.path.join(FAKEROOT, CACHEURLBASE)
        #if not os.path.exists(content):os.path.join(FAKEROOT, CONTENT
        #    raise RuntimeError("{} does not exist. Please use the correct run-radiopadre script, or report a bug.".format(content))

    if not os.access(CACHEBASE, os.W_OK):
        raise RuntimeError("{} is not user-writeable. Please use the correct run-radiopadre script, or report a bug.".format(CACHEBASE))

    _setup_done = True

    ## Uncomment the line below when debugging paths setup
    # display_setup()


def get_cache_dir(path, subdir=None):
    """
    Creates directory for caching radiopadre stuff associated with the given file.

    Returns tuple of (real_path, url_path). The former is the real filesystem location of the directory.
    The latter is the URL to this directory.
    """
    basedir = os.path.dirname(path)
    # make basedir fully qualified, and make basedir_rel relative to ROOTDIR
    if not basedir or basedir == ".":
        basedir = ROOTDIR
        basedir_rel = "."
    else:
        rootdir = ROOTDIR + "/"
        basedir = os.path.abspath(basedir)
        if not basedir.startswith(rootdir):
            raise RuntimeError("Trying to access {}, which is outside the {} hierarchy".format(path, ROOTDIR))
        basedir_rel = basedir[len(rootdir):]

    cachedir = os.path.join(basedir, ".radiopadre")
    cacheurl = os.path.normpath(os.path.join(URLBASE, basedir_rel, ".radiopadre"))

    # cachedir doesn't exist, but we can create it
    if not os.path.exists(cachedir) and os.access(basedir, os.W_OK):
        os.mkdir(cachedir)

    # same for subdir
    if subdir:
        cacheurl = os.path.join(cacheurl, subdir)
        subdir_full = os.path.join(cachedir, subdir)
        if not os.path.exists(subdir_full) and os.access(cachedir, os.W_OK):
            os.mkdir(subdir_full)
        cachedir = subdir_full

    # cachedir is writeable by us -- use it
    if os.path.exists(cachedir) and os.access(cachedir, os.W_OK):
        return cachedir, cacheurl

    # ok, fall back to creating cache under CACHEBASE, which is guaranteed to be ours at least -- if it's not writeable,
    # we can fail and let the user sort it out
    cachedir = os.path.normpath(os.path.join(CACHEBASE, basedir_rel, subdir or "."))
    cacheurl = os.path.normpath(os.path.join(CACHEURLBASE, basedir_rel, subdir or "."))
    if not os.path.exists(cachedir):
        os.system("mkdir -p {}".format(cachedir))
    if not os.access(cachedir, os.W_OK):
        # TODO: maybe rm -fr the f*cker?
        raise RuntimeError("{} is not writeable. Try removing it.".format(cachedir))

    #print cachedir, cacheurl, basedir_rel
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
