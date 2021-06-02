import os, traceback, atexit, logging, sys

import iglesia
from iglesia.utils import message, warning, error

# these are set up in init
ROOTDIR = None

# SERVER_BASEDIR is set up in iglesia (as e.g. /home/user/path)

SHADOW_URL_PREFIX = None    # URL prefix for HTTP server serving shadow tree (e.g. http://localhost:port/{SESSION_ID})
FILE_URL_ROOT = None        # root URL for accessing files through Jupyter (e.g. /files/to)
NOTEBOOK_URL_ROOT = None    # root URL for accessing notebooks through Jupyter (e.g. /notebooks/to)
CACHE_URL_BASE = None       # base URL for cache, e.g. http://localhost:port/{SESSION_ID}/home/user/path
CACHE_URL_ROOT = None       # URL for cache of root dir, e.g. http://localhost:port/{SESSION_ID}/home/user/path/to

NBCONVERT = None            # set to True if running in notebook-convert mode (i.e. non-interactive)

TERMINAL_URL = None         # URL to open a terminal

NOTEBOOK_NAME = None        # path to notebook

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

    global FILE_URL_ROOT, NOTEBOOK_URL_ROOT, CACHE_URL_BASE, CACHE_URL_ROOT, \
        SHADOW_URL_PREFIX, TERMINAL_URL
    global \
        ABSROOTDIR, ROOTDIR, DISPLAY_ROOTDIR, SHADOW_HOME, SERVER_BASEDIR, SHADOW_BASEDIR, \
        SHADOW_ROOTDIR, SESSION_DIR, SESSION_URL, SESSION_ID, \
        VERBOSE, HOSTNAME, SNOOP_MODE

    from iglesia import \
        ABSROOTDIR, ROOTDIR, DISPLAY_ROOTDIR, SHADOW_HOME, SERVER_BASEDIR, SHADOW_BASEDIR, \
        SHADOW_ROOTDIR, SESSION_DIR, SESSION_URL, SESSION_ID, \
        VERBOSE, HOSTNAME, SNOOP_MODE

    # setup for snoop mode. Browsing /home/other/path/to,
    if SNOOP_MODE:
        # for a Jupyter basedir of ~/.radiopadre/home/other/path, this becomes /home/other/path
        unshadowed_server_base = SERVER_BASEDIR[len(SHADOW_HOME):]
        # Otherwise it'd better have been /home/other/path/to to begin with!
        if not _is_subdir(ABSROOTDIR, unshadowed_server_base):
            error(f"""The requested directory {ABSROOTDIR} is not under {unshadowed_server_base}.
                This is probably a bug! """)
        # Since Jupyter is running under ~/.radiopadre/home/other/path, we can serve other's files from
        # /home/other/path/to as /files/to/.content
        subdir = SHADOW_ROOTDIR[len(SERVER_BASEDIR):]   # this becomes "/to" (or "" if paths are the same)
        # but do make sure that the .content symlink is in place!
        _make_symlink(ABSROOTDIR, SHADOW_ROOTDIR + "/.radiopadre.content")
    # else running in native mode
    else:
        if not _is_subdir(ABSROOTDIR, SERVER_BASEDIR):
            warning(f"""The requested directory {ABSROOTDIR} is not under {SERVER_BASEDIR}.
                This is probably a bug! """)
        # for a server dir of /home/user/path, and an ABSROOTDIR of /home/oms/path/to, get the subdir
        subdir = ABSROOTDIR[len(SERVER_BASEDIR):]   # this becomes "/to" (or "" if paths are the same)

    os.chdir(ABSROOTDIR)
    ROOTDIR = '.'

    ## check casacore availability
    global casacore_tables
    try:
        import casacore.tables as casacore_tables
    except Exception as exc:
        casacore_tables = None
        warning("casacore.tables failed to import. Table browsing functionality will not be available.")

    radiopadre_base = os.path.dirname(os.path.dirname(__file__))

    # when running nbconvert, it doesn't know about the magic "/files" URL, and just needs a local filename
    global NBCONVERT
    NBCONVERT = bool(os.environ.get("RADIOPADRE_NBCONVERT"))
    files_prefix = "." if NBCONVERT else "/files"

    # # pre-init JS9 stuff and run JS9 helper
    # js9.preinit_js9(in_container, helper_port, userside_helper_port, http_rewrites)

    iglesia.init_helpers(radiopadre_base, interactive=not NBCONVERT)

    # now a port is available (set up in init_helpers()), form up URLs

    TERMINAL_URL = f"{iglesia.LOCALHOST_URL}:{iglesia.WETTY_PORT}/{SESSION_ID}/wetty"
    SHADOW_URL_PREFIX = f"{iglesia.LOCALHOST_URL}:{iglesia.HTTPSERVER_PORT}/{SESSION_ID}"
    CACHE_URL_ROOT = SHADOW_URL_PREFIX + ABSROOTDIR
    CACHE_URL_BASE = CACHE_URL_ROOT[:-len(subdir)] if subdir else CACHE_URL_ROOT

    if SNOOP_MODE:
        FILE_URL_ROOT = f"{files_prefix}{subdir}/.radiopadre.content/"
        NOTEBOOK_URL_ROOT = f"/notebooks{subdir}/.radiopadre.content/"
    else:
        FILE_URL_ROOT = f"{files_prefix}{subdir}/"
        NOTEBOOK_URL_ROOT = f"/notebooks{subdir}/"

    global NOTEBOOK_NAME
    NOTEBOOK_NAME = os.environ.get("RADIOPADRE_NOTEBOOK_NAME") or None
    message(f"notebook name is {NOTEBOOK_NAME}")

    if NBCONVERT and NOTEBOOK_NAME:
        atexit.register(_save_mirror_manifest)
        message(f"registered exit handler")

    # init JS9 sources
    from . import js9
    js9.preinit_js9()

    # figure out CARTA version
    carta_version = f"{sys.prefix}/carta_version"
    if os.path.exists(carta_version):
        iglesia.CARTA_VERSION = open(carta_version, "rt").read()
        message(f"Detected CARTA version {iglesia.CARTA_VERSION}")
    else:
        iglesia.CARTA_VERSION = "1.x"
        message(f"Assuming CARTA version {iglesia.CARTA_VERSION}, as none was detected")


_mirror_manifest = set()


def add_mirror_file(path):
    # things in cache still accessible via symlinks
    if path.startswith(SHADOW_BASEDIR):
        path = os.path.relpath(path, SHADOW_BASEDIR)
    _mirror_manifest.add(path)


def _save_mirror_manifest():
    manifest = f"{NOTEBOOK_NAME}.manifest"
    try:
        from radiopadre.file import FileBase
        if os.path.exists(NOTEBOOK_NAME):
            add_mirror_file(NOTEBOOK_NAME)
        files = list(_mirror_manifest) + list(FileBase.mirrorable_files())

        # take relative path if we can
        # files = [os.path.relpath(x, ABSROOTDIR) for x in files]

        with open(manifest, "wt") as ff:
            ff.write(f"{NOTEBOOK_NAME}\n")
            if NBCONVERT:
                ff.write(f"{os.path.splitext(NOTEBOOK_NAME)[0]}.html\n")
            ff.write("\n".join(files))
    except Exception as exc:
        with open(manifest + ".error", "wt") as ff:
            ff.write(f"Error writing manifest:\n{traceback.format_exception()}")


if ROOTDIR is None:
    from iglesia import logger
    # enable logging
    log = logger.init("radiopadre.kernel") #, use_formatter=False)
    log.setLevel(logging.DEBUG)
    log.addHandler(log_handler)
    LOGFILE = logger.enable_logfile("kernel")
    logger.disable_printing()
    message("initializing radiopadre_kernel")
    init()
