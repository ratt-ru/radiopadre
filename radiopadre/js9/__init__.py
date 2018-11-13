import os
import os.path
import traceback
import radiopadre
from radiopadre.render import render_status_message

# init JS9 configuration

# js9 source directory
DIRNAME = os.path.dirname(__file__)

JS9_ERROR = os.environ.get("RADIOPADRE_JS9_ERROR") or None

# these globals define the access method for JS9
_prefix = os.environ["RADIOPADRE_JS9_HTTP"]

RADIOPADRE_INSTALL_PREFIX_HTTP = _prefix+".radiopadre/radiopadre-www" # URL used to access radiopadre code
RADIOPADRE_LOCAL_PREFIX_HTTP = _prefix+".radiopadre"               # URL used to access radiopadre aux dir
JS9_INSTALL_PREFIX_HTTP = _prefix+".radiopadre/js9-www"  # URL used to access JS9 code
JS9_FITS_PREFIX_HTTP    = _prefix                        # URL used to access FITS files inside scripts

# can't access scripts via Jupyter because they get sandboxed -- we'll have to inject html into iframes or documents when we go this route
JS9_SCRIPT_PREFIX = JS9_SCRIPT_PREFIX_HTTP  = _prefix                        # URL used to access JS9 launch scripts
JS9_SCRIPT_SUFFIX = "js9-http.html"                                          # suffix for the auto-generated launch scripts

# else:
#
#     JS9_ERROR = "invalid RADIOPADRE_JS9_ACCESS setting. Please use 'jupyter' or e.g. 'http://localhost:port'"

if not JS9_ERROR:
    try:
        JS9_HELPER_PORT = int(os.environ["RADIOPADRE_JS9_HELPER_PORT"])
    except:
        JS9_ERROR = "invalid RADIOPADRE_JS9_HELPER_PORT setting, integer value expected"


# get init code, substitute global variables into it
if not JS9_ERROR:
    try:
        with open(os.path.join(DIRNAME, "js9-init-template.html")) as inp:
            source = inp.read()
        JS9_INIT_HTML_HTTP = source.format(JS9_INSTALL_PREFIX=JS9_INSTALL_PREFIX_HTTP,
                                           RADIOPADRE_INSTALL_PREFIX=RADIOPADRE_INSTALL_PREFIX_HTTP,
                                           RADIOPADRE_LOCAL_PREFIX=RADIOPADRE_LOCAL_PREFIX_HTTP,
                                           **globals())

    except Exception, exc:
        traceback.print_exc()
        JS9_ERROR = "Error reading init templates: {}".format(str(exc))

# on error, init code replaced by error message
if JS9_ERROR:
    JS9_INIT_HTML_HTTP = render_status_message("Error initializing JS9: {}".format(JS9_ERROR), bgcolor='yellow')
    radiopadre.add_startup_warning("""Warning: the JS9 FITS viewer is not functional ({}). Live FITS file viewing
        will not be available in this notebook. You probably want to fix this problem (missing libcfitsio-dev and/or nodejs
        packages, typically), then reinstall the radiopadre environment on this system ({}).
        """.format(JS9_ERROR, os.environ['HOSTNAME']))

