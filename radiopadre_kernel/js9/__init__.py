import os, os.path, traceback

from iglesia.utils import message, error
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

def preinit_js9():
    """Pre-initialization, when Javascript is not available yet. Determines paths and starts helper processs"""
    global radiopadre_kernel
    import radiopadre_kernel
    import iglesia

    global JS9_HELPER_PORT, JS9_DIR
    JS9_DIR = iglesia.JS9_DIR
    JS9_HELPER_PORT = iglesia.JS9HELPER_PORT

    try:
        global JS9_ERROR
        if not os.path.exists(JS9_DIR):
            raise JS9Error(f"{JS9_DIR} does not exist")

        message(f"Using JS9 install in {JS9_DIR}")

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

        JS9_LOCAL_SETTINGS = f"{radiopadre_kernel.SESSION_URL}/js9prefs.js"

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
        error(f"JS9 init error: {JS9_ERROR}")

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