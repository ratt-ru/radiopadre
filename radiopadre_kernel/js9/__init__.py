import os, os.path, sys, traceback


# init JS9 configuration

# js9 source directory
DIRNAME = os.path.dirname(__file__)

JS9_DIR = None
JS9_ERROR = os.environ.get("RADIOPADRE_JS9_ERROR") or None
JS9_HELPER_PORT = None
# Javascript code read from local settings file
JS9_LOCAL_SETTINGS = None
JS9_INIT_HTML_STATIC = JS9_INIT_HTML_DYNAMIC = ""

class JS9Error(Exception):
    def __init__(self, message=None):
        self.message = message

def preinit_js9(in_container, helper_port, userside_helper_port, http_rewrites=[], start_helper=True):
    """Pre-initialization, when Javascript is not available yet. Determines paths and starts helper processs"""
    global radiopadre_kernel
    import radiopadre_kernel
    from radiopadre_client.utils import find_which, chdir

    global JS9_HELPER_PORT
    JS9_HELPER_PORT = userside_helper_port

    try:
        global JS9_ERROR, JS9_DIR
        if JS9_ERROR:
            raise JS9Error()

        JS9_DIR = os.environ.get('RADIOPADRE_JS9_DIR') or f"{sys.prefix}/js9-www"

        if not os.path.exists(JS9_DIR):
            raise JS9Error(f"{JS9_DIR} does not exist")
        js9helper = f"{JS9_DIR}/js9Helper.js"
        if not os.path.exists(js9helper):
            raise JS9Error(f"{js9helper} does not exist")

        radiopadre_kernel.log.info(f"Using JS9 install in {JS9_DIR}")

        js9prefs = f"{radiopadre_kernel.LOCAL_SESSION_DIR}/js9prefs.js"
        if not in_container:
            # create JS9 settings file (in container mode, this is created and mounted inside container already)
            open(js9prefs, "w").write(f"JS9Prefs.globalOpts.helperPort = {userside_helper_port};\n")

        import notebook
        http_rewrites.append("/js9-www/={}/".format(JS9_DIR))
        http_rewrites.append(
            "/js9colormaps.js={}/static/js9colormaps.js".format(os.path.dirname(notebook.__file__)))

        radiopadre_kernel.log.info(f"Starting {js9helper} on port {helper_port} in {radiopadre_kernel.SHADOW_ROOTDIR}")
        nodejs = find_which("nodejs") or find_which("node")
        if not nodejs:
            raise JS9Error("Unable to find nodejs or node -- can't run js9helper.")
        try:
            with chdir(radiopadre_kernel.SHADOW_ROOTDIR):
                radiopadre_kernel.start_child_process(nodejs.strip(), js9helper,
                     f'{{"helperPort": {helper_port}, "debug": {radiopadre_kernel.VERBOSE}, ' +
                     f'"fileTranslate": ["^(http://localhost:[0-9]+/[0-9a-f]+{radiopadre_kernel.ABSROOTDIR}|/static/)", ""] }}')
        except Exception as exc:
            raise JS9Error(f"error running {nodejs} {js9helper}: {exc}")

        global _prefix
        global RADIOPADRE_INSTALL_PREFIX
        global RADIOPADRE_LOCAL_PREFIX
        global JS9_INSTALL_PREFIX
        global JS9_INIT_HTML_STATIC
        global JS9_INIT_HTML_DYNAMIC
        global JS9_SCRIPT_PREFIX
        global JS9_LOCAL_SETTINGS

        RADIOPADRE_INSTALL_PREFIX = f"{radiopadre_kernel.SHADOW_URL_PREFIX}/radiopadre-www" # URL used to access radiopadre code
        RADIOPADRE_LOCAL_PREFIX = f"{radiopadre_kernel.SHADOW_URL_PREFIX}/{radiopadre_kernel.ABSROOTDIR}/.radiopadre"  # URL used to access radiopadre aux dir
        JS9_INSTALL_PREFIX = f"{radiopadre_kernel.SHADOW_URL_PREFIX}/js9-www"  # URL used to access JS9 code
        JS9_SCRIPT_PREFIX = radiopadre_kernel.SHADOW_URL_PREFIX

        JS9_LOCAL_SETTINGS = f"{radiopadre_kernel.LOCAL_SESSION_URL}/js9prefs.js"

        # load templated init HTML
        try:
            with open(os.path.join(DIRNAME, "js9-init-static-template.html"), "rt") as inp:
                JS9_INIT_HTML_STATIC = inp.read().format(**globals())
            with open(os.path.join(DIRNAME, "js9-init-dynamic-template.html"), "rt") as inp:
                JS9_INIT_HTML_DYNAMIC = inp.read().format(**globals())

        except Exception as exc:
            traceback.print_exc()
            JS9_ERROR = "Error reading init templates: {}".format(str(exc))

    except JS9Error as exc:
        if exc.message:
            JS9_ERROR = exc.message

    # on error, init code replaced by error message

    if JS9_ERROR:
        # JS9_INIT_HTML_HTTP = render_status_message("Error initializing JS9: {}".format(JS9_ERROR), bgcolor='yellow')
        JS9_INIT_HTML = f"Error initializing JS9: {JS9_ERROR}"
        radiopadre_kernel.log.warning(f"""The JS9 FITS viewer is not functional ({JS9_ERROR}). Live FITS file viewing
            will not be available in this notebook. You probably want to fix this problem (missing libcfitsio-dev and/or nodejs
            packages, typically), then reinstall the radiopadre environment on this system ({radiopadre_kernel.HOSTNAME}).""")

# def init_js9():
#     """Final initialization, when Javascript can be injected"""
#     from IPython.display import Javascript, display
#     display(Javascript("""
#       <link type='image/x-icon' rel='shortcut icon' href='/static/js9-www/favicon.ico'>
#       <link type='text/css' rel='stylesheet' href='/static/js9-www/js9support.css'>
#       <link type='text/css' rel='stylesheet' href='/static/js9-www/js9.css'>
#       <link rel='apple-touch-icon' href='/static/js9-www/images/js9-apple-touch-icon.png'>
#       <script type='text/javascript' src='/static/js9-www/js9prefs.js'></script>
#       <script type='text/javascript'> console.log('loaded JS9 prefs 1') </script>
#       <script type='text/javascript' src='/files/.radiopadre-session/js9prefs.js'></script>
#       <script type='text/javascript'> console.log('loaded JS9 prefs 2')</script>
#       <script type='text/javascript' src='/static/js9-www/js9support.min.js'></script>
#       <script type='text/javascript' src='/static/js9-www/js9.min.js'></script>
#       <script type='text/javascript' src='/static/js9-www/js9plugins.js'></script>
#       <script type='text/javascript'> console.log('loaded JS9 components') </script>
#       <script type='text/javascript' src='/static/radiopadre-www/js9partners.js'></script>
#       <script type='text/javascript'> console.log('loaded JS9 partner plugin') </script>
#       <script type='text/javascript' src='/static/js9colormaps.js'></script>\
#     """),)