import json
import nbformat
import os
import pkg_resources

import radiopadre_kernel

from IPython.display import display, HTML, Javascript

from radiopadre_utils.notebook_utils import scrub_cell

from radiopadre import settings_manager
from radiopadre.render import render_error, show_exception, TransientMessage, render_status_message, render_table

# this stuff is setup by the kernel, pull from it

from radiopadre_kernel import SESSION_ID, VERBOSE, HOSTNAME, \
    LOGFILE, ABSROOTDIR, ROOTDIR, DISPLAY_ROOTDIR, SHADOW_HOME, SERVER_BASEDIR, \
    SHADOW_BASEDIR, SHADOW_ROOTDIR, SHADOW_URL_PREFIX, \
    FILE_URL_ROOT, NOTEBOOK_URL_ROOT, CACHE_URL_BASE, CACHE_URL_ROOT, \
    SESSION_DIR, SESSION_URL, NBCONVERT

# init settings
settings = settings_manager.RadiopadreSettingsManager()

try:
    __version__ = pkg_resources.require("radiopadre")[0].version
except pkg_resources.DistributionNotFound:
    __version__ = "development"

## various notebook-related init
try:
    import astropy
    astropy.log.setLevel('ERROR')
except ImportError:
    radiopadre_kernel.log.warning("Failed to import astropy")

# NONE OF THE DIR NAMES ABOVE SHALL HAVE A TRALING SLASH!!!

def _strip_slash(path):
    return path if path == "/" or path is None else path.rstrip("/")

def _is_subdir(subdir, parent):
    return subdir == parent or subdir.startswith(parent+"/")

from radiopadre_kernel import _make_symlink

def display_status():
    # setup status
    data = [ ("cwd", os.getcwd()) ]
    for varname in """SESSION_ID ROOTDIR ABSROOTDIR DISPLAY_ROOTDIR SHADOW_HOME 
                      SERVER_BASEDIR SHADOW_BASEDIR SHADOW_ROOTDIR 
                      SHADOW_URL_PREFIX FILE_URL_ROOT CACHE_URL_BASE CACHE_URL_ROOT 
                      SESSION_DIR SESSION_URL""".split():
        data.append((varname, globals()[varname]))

    data += [("", "startup log follows:")]
    data += radiopadre_kernel.log_handler.get_records()

    from IPython.display import HTML
    display(HTML(render_table(data, ["", ""], numbering=False)))

def display_log(debug=False):
    from IPython.display import HTML
    data = radiopadre_kernel.log_handler.get_records("DEBUG" if debug else "INFO")
    display(HTML(render_table(data, ["", ""], numbering=False)))

show_status = display_status
show_log = display_log

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


def _display_reset():
    display(Javascript("document.radiopadre.reset_display_settings();"))

def _init_js_side():
    """Checks that Javascript components of radiopadre are initialized, does various other init"""
    global _init_js_side_done
    if _init_js_side_done:
        print("init_js_side already done")
        return
    _init_js_side_done = True
    try:
        get_ipython
    except:
        print("get_ipython not found")
        return None
    get_ipython().magic("matplotlib inline")

    settings.display.reset = _display_reset, settings_manager.DocString("call this to reset sizes explicitly")

    html = """<script type='text/javascript'>
            document.radiopadre.register_user('{}');
            document.radiopadre.reset_display_settings();
            </script>
         """.format(os.environ['USER'])


    # reload styles -- loaded from radiopadre-kernel.js already, but reloading is useful for debugging
    styles_file = os.path.join(os.path.dirname(__file__), "html/radiopadre.css")
    html += f"""<style>
        {open(styles_file).read()}
    </style>"""

    html += """<DIV onload=radiopadre.document.reset_display_settings></DIV>"""

    from radiopadre import layouts
    html += layouts.init_html

    from radiopadre_kernel import js9
    if not js9.JS9_ERROR:
        html += js9.JS9_INIT_HTML_DYNAMIC

    # get buttons from various modules
    if not NBCONVERT:
        from . import fitsfile
        html += fitsfile.add_general_buttons()

    # get list of warnings and errors from init
    errors = radiopadre_kernel.log_handler.get_records('WARNING')
    if errors:
        html += render_table(errors, ["", ""], numbering=False)

    display(HTML(html))

def hide_cell_code(hide=True):
    display(Javascript(f"document.radiopadre.set_show_code({int(not hide)});"))

def set_window_sizes(cell_width, window_width, window_height):
    if settings.display.auto_reset:
        settings.display.cell_width, settings.display.window_width, settings.display.window_height = \
            cell_width, window_width, window_height


# def protect(author=None):
#     """Makes current notebook protected with the given author name. Protected notebooks won't be saved
#     unless the user matches the author."""
#     author = author or os.environ['USER']
#     display(Javascript("document.radiopadre.protect('%s')" % author))
#     display(HTML(render_status_message("""This notebook is now protected, author is "%s".
#         All other users will have to treat this notebook as read-only.""" % author)))
#
#
# def unprotect():
#     """Makes current notebook unprotected."""
#     display(Javascript("document.radiopadre.unprotect()"))
#     display(HTML(render_status_message("""This notebook is now unprotected.
#         All users can treat it as read-write.""")))
#


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


__init = False
# print("importing radiopadre")

if not __init:
    from radiopadre_kernel import casacore_tables
    radiopadre_kernel.log.info("initializing radiopadre JS side")
    # print("initializing radiopadre")
    _init_js_side()
    __init = True

# import stuff

from .file import autodetect_file_type
from .datadir import DataDir, ls, lsR, lst, lsrt
from .filelist import FileList
from .fitsfile import FITSFile
from .imagefile import ImageFile
from .casatable import CasaTable
from .htmlfile import HTMLFile, URL
from .table import tabulate
from .render import render_table, render_preamble, render_refresh_button, render_status_message, rich_string, render_url, render_title

