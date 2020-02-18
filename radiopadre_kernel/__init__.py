import os, traceback, atexit, logging

from radiopadre_client.utils import message, warning, error, debug, DEVNULL, DEVZERO
from radiopadre_client import iglesia

# these are set up in init
ROOTDIR = None

# SERVER_BASEDIR is set up in iglesia (as e.g. /home/user/path)

SHADOW_BASEDIR = None   # shadow equivalent of SERVER_BASEDIR, i.e. ~/.radiopadre/home/user/path

SHADOW_URL_PREFIX = None    # URL prefix for HTTP server serving shadow tree (e.g. http://localhost:port/{SESSION_ID})
FILE_URL_ROOT = None        # root URL for accessing files through Jupyter (e.g. /files/to)
NOTEBOOK_URL_ROOT = None    # root URL for accessing notebooks through Jupyter (e.g. /notebooks/to)
CACHE_URL_BASE = None       # base URL for cache, e.g. http://localhost:port/{SESSION_ID}/home/user/path
CACHE_URL_ROOT = None       # URL for cache of root dir, e.g. http://localhost:port/{SESSION_ID}/home/user/path/to

casacore_tables = None

class PadreLogHandler(logging.Handler):
    def __init__(self):
        super(PadreLogHandler, self).__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)

    def get_records(self, min_level=logging.INFO):
        """Returns accumulated records from the specified level (or higher)"""
        if type(min_level) is str:
            min_level = getattr(logging, min_level)
        return [(logging.getLevelName(rec.levelno), rec.msg) for rec in self.records if rec.levelno >= min_level]

log_handler = PadreLogHandler()

_child_processes = []

def terminate_child_processes():
    message("terminating {} child processes".format(len(_child_processes)))
    for proc in _child_processes:
        proc.terminate()
    for proc in _child_processes:
        proc.wait()

atexit.register(terminate_child_processes)

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
    except Exception as exc:
        traceback.print_exc()
        raise

def init():
    """Initializes radiopadre kernel"""
    iglesia.init()

    global FILE_URL_ROOT, NOTEBOOK_URL_ROOT, CACHE_URL_BASE, CACHE_URL_ROOT, SHADOW_URL_PREFIX
    global \
        ABSROOTDIR, ROOTDIR, DISPLAY_ROOTDIR, SHADOW_HOME, SERVER_BASEDIR, \
        SHADOW_BASEDIR, SHADOW_ROOTDIR, SESSION_DIR, SESSION_URL, SESSION_ID, \
        VERBOSE, HOSTNAME, CARTA_PORT, CARTA_WS_PORT, ALIEN_MODE

    from radiopadre_client.iglesia import \
        ABSROOTDIR, ROOTDIR, DISPLAY_ROOTDIR, SHADOW_HOME, SERVER_BASEDIR, \
        SHADOW_ROOTDIR, SESSION_DIR, SESSION_URL, SESSION_ID, \
        VERBOSE, HOSTNAME, CARTA_PORT, CARTA_WS_PORT, \
        HTTPSERVER_PORT, ALIEN_MODE

    # setup for alien mode. Browsing /home/alien/path/to, where "alien" is a different user
    if ALIEN_MODE:
        # for a Jupyter basedir of ~/.radiopadre/home/alien/path, this becomes /home/alien/path
        unshadowed_server_base = SERVER_BASEDIR[len(SHADOW_HOME):]
        SHADOW_BASEDIR = SERVER_BASEDIR
        # Otherwise it'd better have been /home/alien/path/to to begin with!
        if not _is_subdir(ABSROOTDIR, unshadowed_server_base):
            error(f"""The requested directory {ABSROOTDIR} is not under {unshadowed_server_base}.
                This is probably a bug! """)
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
            warning(f"""The requested directory {ABSROOTDIR} is not under {SERVER_BASEDIR}.
                This is probably a bug! """)
        # for a server dir of /home/user/path, and an ABSROOTDIR of /home/oms/path/to, get the subdir
        subdir = ABSROOTDIR[len(SERVER_BASEDIR):]   # this becomes "/to" (or "" if paths are the same)
        FILE_URL_ROOT = "/files" + subdir
        NOTEBOOK_URL_ROOT = "/notebooks" + subdir
        SHADOW_BASEDIR = SHADOW_HOME + SERVER_BASEDIR

    os.chdir(ABSROOTDIR)
    ROOTDIR = '.'

    SHADOW_URL_PREFIX = f"http://localhost:{HTTPSERVER_PORT}/{SESSION_ID}"

    # check if we have a URL to access the shadow tree directly. If not, we can use "limp-home" mode
    # (i.e. the Jupyter server itself to access cache), but some things won't work
    if SHADOW_URL_PREFIX is None:
        if not os.access(ABSROOTDIR, os.W_OK):
            warning(f"""The notebook is in a non-writeable directory {ABSROOTDIR}. Radiopadre needs a shadow HTTP
                server to deal with this situation, but this doesn't appear to have been set up.
                This is probably because you've attempted to load a radiopadre notebook from a 
                vanilla Jupyter session. Please use the run-radiopadre-server script to start Jupyter instead 
                (or report a bug if that's what you're already doing!)""")
        else:
            warning(f"""The radiopadre shadow HTTP server does not appear to be set up properly.
                                  Running with restricted functionality (e.g. JS9 will not work).""")
        CACHE_URL_BASE = "/files"
        CACHE_URL_ROOT = "/files" + subdir
    else:
        CACHE_URL_ROOT = SHADOW_URL_PREFIX + ABSROOTDIR
        CACHE_URL_BASE = CACHE_URL_ROOT[:-len(subdir)] if subdir else CACHE_URL_ROOT

    ## check casacore availability
    global casacore_tables
    try:
        import casacore.tables as casacore_tables
    except Exception as exc:
        casacore_tables = None
        warning("casacore.tables failed to import. Table browsing functionality will not be available.")

    radiopadre_base = os.path.dirname(os.path.dirname(__file__))

    # # pre-init JS9 stuff and run JS9 helper
    # js9.preinit_js9(in_container, helper_port, userside_helper_port, http_rewrites)

    global _child_processes
    _child_processes += iglesia.init_helpers(radiopadre_base)


if ROOTDIR is None:
    import radiopadre_client.utils, radiopadre_client.logger
    # enable logging
    log = radiopadre_client.logger.init("radiopadre.kernel") #, use_formatter=False)
    log.setLevel(logging.DEBUG)
    log.addHandler(log_handler)
    LOGFILE = radiopadre_client.logger.enable_logfile("kernel")
    radiopadre_client.logger.disable_printing()
    message("initializing radiopadre_kernel")
    init()
