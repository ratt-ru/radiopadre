import os, subprocess, traceback, atexit, uuid, logging

from radiopadre_client.utils import message, DEVNULL, DEVZERO

# this stuff is setup by init() below

SESSION_ID = None          # session ID. Used below in various paths
VERBOSE = 0                # message verbosity level, >0 for debugging
CARTA_PORT = CARTA_WS_PORT = None  # carta ports, if set up
HOSTNAME = "localhost"

LOGFILE = None             # file to log output to

# NONE OF THE DIR NAMES BELOW SHALL HAVE A TRALING SLASH!!!
# Use _strip_slash() when in doubt.

ABSROOTDIR = None       # absolute path to "root" directory, e.g. /home/user/path/to
ROOTDIR = None          # relative path to "root" directory (normally .)
DISPLAY_ROOTDIR = None  # what the root directory should be rewritten as, for display purposes
SHADOW_HOME = None      # base dir for the shadow directory tree

SERVER_BASEDIR = None   # dir where the Jupyter server is running, e.g. /home/user/path (or ~/.radiopadre/home/user/path)
SHADOW_BASEDIR = None   # shadow equivalent of above, i.e. ~/.radiopadre/home/user/path in both cases
SHADOW_ROOTDIR = None   # "root" directory in shadow tree, e.g. ~/.radiopadre/home/user/path/to
# The distinction above is important. The Jupyter session can be started in some *base* directory, while
# notebooks may be launched in a subdirectory of the latter. We need to know about this, because the
# subdirectory needs to be included in URLs given to Jupyter/JS9 helper/etc. to access the files within
# the subdirectory correctly.

SHADOW_URL_PREFIX = None   # URL prefix for HTTP server serving shadow tree (e.g. http://localhost:port/{SESSION_ID})
FILE_URL_ROOT = None       # root URL for accessing files through Jupyter (e.g. /files/to)
NOTEBOOK_URL_ROOT = None   # root URL for accessing notebooks through Jupyter (e.g. /notebooks/to)
CACHE_URL_BASE = None      # base URL for cache, e.g. http://localhost:port/{SESSION_ID}/home/user/path
CACHE_URL_ROOT = None      # URL for cache of root dir, e.g. http://localhost:port/{SESSION_ID}/home/user/path/to

LOCAL_SESSION_DIR = None   # session dir -- usually {SHADOW_ROOTDIR}/.radiopadre-session
LOCAL_SESSION_URL = None   # usually {SHADOW_URL_PREFIX}/{ABSROOTDIR}/.radiopadre-session

_messages = []

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

def start_child_process(*args, log=True, stdin=DEVZERO):
    """Helper method. Starts a child process from the kernel"""
    message("starting {}".format(" ".join(args)))
    _child_processes.append(subprocess.Popen(args, stdin=stdin,
                                             stdout=LOGFILE if log else DEVNULL,
                                             stderr=LOGFILE))

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


def init(rootdir=None, verbose=True):
    """Initializes radiopadre kernel"""

    global ABSROOTDIR
    global ROOTDIR
    global DISPLAY_ROOTDIR
    global SHADOW_HOME
    global SERVER_BASEDIR
    global SHADOW_BASEDIR
    global SHADOW_ROOTDIR
    global LOCAL_SESSION_DIR, LOCAL_SESSION_URL

    global SHADOW_URL_PREFIX
    global FILE_URL_ROOT
    global NOTEBOOK_URL_ROOT
    global SESSION_ID
    global CACHE_URL_ROOT
    global CACHE_URL_BASE

    global VERBOSE
    global SESSION_ID
    global HOSTNAME
    global CARTA_PORT, CARTA_WS_PORT

    from radiopadre_client.utils import find_unused_ports, make_dir
    from . import js9

    LOCAL_SESSION_DIR = os.environ.get('RADIOPADRE_SHADOW_SESSION_DIR')
    if not LOCAL_SESSION_DIR:
        LOCAL_SESSION_DIR = os.getcwd() + "/.radiopadre-session"
        make_dir(LOCAL_SESSION_DIR)

    # get session ID, or setup a new one
    SESSION_ID = os.environ.get('RADIOPADRE_SESSION_ID')
    if not SESSION_ID:
        os.environ['RADIOPADRE_SESSION_ID'] = SESSION_ID = uuid.uuid4().hex

    # set verbosity
    VERBOSE = int(os.environ.get('RADIOPADRE_VERBOSE') or 0)

    # set ports, else allocate ports
    selected_ports = os.environ.get('RADIOPADRE_SELECTED_PORTS')
    if selected_ports:
        selected_ports = map(int, selected_ports.strip().split(":"))
    else:
        selected_ports = find_unused_ports(4)
    helper_port, http_port, carta_port, carta_ws_port = selected_ports

    userside_ports = os.environ.get('RADIOPADRE_USERSIDE_PORTS')
    if userside_ports:
        userside_ports = map(int, userside_ports.strip().split(":"))
    else:
        userside_ports = selected_ports
    userside_helper_port, userside_http_port, CARTA_PORT, CARTA_WS_PORT = userside_ports

    # set hostname
    HOSTNAME = os.environ.get('HOSTNAME')
    if not HOSTNAME:
        os.environ["HOSTNAME"] = HOSTNAME = subprocess.check_output("/bin/hostname").decode().strip()

    # set root directories
    rootdir =_strip_slash(os.path.abspath(rootdir or '.'))
    if ABSROOTDIR is not None and os.path.samefile(rootdir, ABSROOTDIR):
        return

    ABSROOTDIR        = rootdir
    SHADOW_HOME       = _strip_slash(os.path.abspath(os.environ.get('RADIOPADRE_SHADOW_HOME') or os.path.expanduser("~/.radiopadre")))
    SERVER_BASEDIR    = _strip_slash(os.path.abspath(os.environ.get('RADIOPADRE_SERVER_BASEDIR') or os.getcwd()))
    DISPLAY_ROOTDIR   = _strip_slash(os.environ.get("RADIOPADRE_DISPLAY_ROOT") or '.')
    SHADOW_URL_PREFIX = f"http://localhost:{userside_http_port}/{SESSION_ID}/"

    ALIEN_MODE = _is_subdir(SERVER_BASEDIR, SHADOW_HOME)

    # if our rootdir is ~/.radiopadre/home/alien/path/to, then change it to /home/alien/path/to
    if _is_subdir(ABSROOTDIR, SHADOW_HOME):
        ABSROOTDIR = ABSROOTDIR[len(SHADOW_HOME):]
    # and this will be ~/.radiopadre/home/alien/path/to
    SHADOW_ROOTDIR = SHADOW_HOME + ABSROOTDIR

    LOCAL_SESSION_URL = f"{SHADOW_URL_PREFIX}{ABSROOTDIR[1:]}/.radiopadre-session"

    # setup for alien mode. Browsing /home/alien/path/to, where "alien" is a different user
    if ALIEN_MODE:
        # for a Jupyter basedir of ~/.radiopadre/home/alien/path, this becomes /home/alien/path
        unshadowed_server_base = SERVER_BASEDIR[len(SHADOW_HOME):]
        SHADOW_BASEDIR = SERVER_BASEDIR
        # Otherwise it'd better have been /home/alien/path/to to begin with!
        if not _is_subdir(ABSROOTDIR, unshadowed_server_base):
            log.error(f"""The requested directory {ABSROOTDIR} is not under {unshadowed_server_base}.
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
            log.warning(f"""The requested directory {ABSROOTDIR} is not under {SERVER_BASEDIR}.
                This is probably a bug! """)
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
            log.warning(f"""The notebook is in a non-writeable directory {ABSROOTDIR}. Radiopadre needs a shadow HTTP
                server to deal with this situation, but this doesn't appear to have been set up.
                This is probably because you've attempted to load a radiopadre notebook from a 
                vanilla Jupyter session. Please use the run-radiopadre-server script to start Jupyter instead 
                (or report a bug if that's what you're already doing!)""")
        else:
            log.warning(f"""The radiopadre shadow HTTP server does not appear to be set up properly.
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
        log.warning("""Warning: casacore.tables failed to import ({}). Table browsing functionality will 
            not be available in this notebook. You probably want to install casacore-dev and python-casacore on this 
            system ({}), then reinstall the radiopadre environment.
            """.format(exc, HOSTNAME))

    ## proceed to start helpers
    from radiopadre_client.utils import chdir, find_which

    in_container = bool(os.environ.get('RADIOPADRE_CONTAINER_NAME'))

    radiopadre_base = os.path.dirname(os.path.dirname(__file__))

    # accumulates rewrite rules for HTTP server
    # add radiopadre/html/ to rewrite as /radiopadre-www/
    http_rewrites = [f"/radiopadre-www/={radiopadre_base}/html/"]

    # pre-init JS9 stuff and run JS9 helper
    js9.preinit_js9(in_container, helper_port, userside_helper_port, http_rewrites)

    # run http server
    workdir = os.environ.get('RADIOPADRE_WORKDIR') or os.path.expanduser("~/.radiopadre")
    log.info(f"Starting HTTP server process in {workdir} on port {http_port}")
    server = find_which("radiopadre-http-server.py")

    if server:
        with chdir(workdir):
            start_child_process(server, str(http_port), *http_rewrites, log=False)
    else:
        log.warning("HTTP server script radiopadre-http-server.py not found, functionality will be restricted")

    ## start CARTA backend

    for carta_exec in os.environ.get('RADIOPADRE_CARTA_EXEC'), f"{radiopadre_base}/carta/carta", find_which('carta'):
        if carta_exec and os.access(carta_exec, os.X_OK):
            break
    else:
        carta_exec = None

    if not carta_exec or not os.path.exists(carta_exec):
        log.warning("CARTA backend not found, omitting")
    else:
        carta_dir = os.environ.get('RADIOPADRE_CARTA_DIR') or os.path.dirname(os.path.dirname(carta_exec))
        log.info(f"Running CARTA via {carta_exec} (in dir {carta_dir})")
        with chdir(carta_dir):
            start_child_process(carta_exec, "--remote",
                                f"--root={ABSROOTDIR}", f"--folder={ABSROOTDIR}",
                                f"--port={carta_ws_port}", "--fport={}".format(carta_port),
                                stdin=subprocess.PIPE)


if ROOTDIR is None:
    import radiopadre_client.utils, radiopadre_client.logger
    # enable logging
    log = radiopadre_client.logger.init("radiopadre.kernel", use_formatter=False)
    log.addHandler(log_handler)
    LOGFILE = radiopadre_client.logger.enable_logfile("kernel")
    radiopadre_client.logger.disable_printing()
    log.info("initializing radiopadre_kernel")
    init(os.getcwd(), False)
