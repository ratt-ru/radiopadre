import os
import os.path
import traceback

# init JS9 configuration

JS9_ERROR = None

# these globals define the access method for JS9
_method = os.environ["RADIOPADRE_JS9_HTTP"]

RADIOPADRE_INSTALL_PREFIX_JUP = "/static/radiopadre-www"           # URL used to access radiopadre code
RADIOPADRE_LOCAL_PREFIX_JUP = "/files/.radiopadre"                 # URL used to access radiopadre aux dir
JS9_INSTALL_PREFIX_JUP = "/static/js9-www"                         # URL used to access JS9 code
JS9_FITS_PREFIX_JUP    = ""                             # URL used to access FITS files inside notebook

RADIOPADRE_INSTALL_PREFIX_HTTP = _method+".radiopadre/radiopadre-www" # URL used to access radiopadre code
RADIOPADRE_LOCAL_PREFIX_HTTP = _method+".radiopadre"               # URL used to access radiopadre aux dir
JS9_INSTALL_PREFIX_HTTP = _method+".radiopadre/js9-www"  # URL used to access JS9 code
JS9_FITS_PREFIX_HTTP    = _method                        # URL used to access FITS files inside scripts

# can't access scripts via Jupyter because they get sandboxed -- we'll have to inject html into iframes or documents when we go this route
JS9_SCRIPT_PREFIX = JS9_SCRIPT_PREFIX_HTTP  = _method                        # URL used to access JS9 launch scripts
JS9_SCRIPT_SUFFIX = "js9-http.html"                                          # suffix for the auto-generated launch scripts

# else:
#
#     JS9_ERROR = "invalid RADIOPADRE_JS9_ACCESS setting. Please use 'jupyter' or e.g. 'http://localhost:port'"

if not JS9_ERROR:
    try:
        JS9_HELPER_PORT = int(os.environ["RADIOPADRE_JS9_HELPER_PORT"])
    except:
        JS9_ERROR = "invalid RADIOPADRE_JS9_HELPER_PORT setting, integer value expected"


# js9 source directory
DIRNAME = os.path.dirname(__file__)

# get init code, substitute global variables into it
if not JS9_ERROR:
    try:
        with open(os.path.join(DIRNAME, "js9-init-template.html")) as inp:
            source = inp.read()
        JS9_INIT_HTML_JUP  = source.format(JS9_INSTALL_PREFIX=JS9_INSTALL_PREFIX_JUP,
                                           RADIOPADRE_INSTALL_PREFIX=RADIOPADRE_INSTALL_PREFIX_JUP,
                                           RADIOPADRE_LOCAL_PREFIX=RADIOPADRE_LOCAL_PREFIX_JUP,
                                           **globals())
        JS9_INIT_HTML_HTTP = source.format(JS9_INSTALL_PREFIX=JS9_INSTALL_PREFIX_HTTP,
                                           RADIOPADRE_INSTALL_PREFIX=RADIOPADRE_INSTALL_PREFIX_HTTP,
                                           RADIOPADRE_LOCAL_PREFIX=RADIOPADRE_LOCAL_PREFIX_HTTP,
                                           **globals())

    except Exception, exc:
        traceback.print_exc()
        JS9_ERROR = "Error reading init templates: {}".format(str(exc))

# on error, init code replaced by error message
if JS9_ERROR:
    JS9_INIT_HTML_JUP = JS9_INIT_HTML_HTTP = "<p>Error initializing JS9: {}</p>".format(JS9_ERROR)


