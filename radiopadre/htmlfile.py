import subprocess
import os.path
import sys
import traceback
import radiopadre

from radiopadre.file import FileBase, ItemBase
from radiopadre.render import render_title, render_url, render_preamble, render_error
from radiopadre import settings
from radiopadre import imagefile
from radiopadre.settings_manager import DocString
from iglesia import message, debug, find_which

phantomjs = find_which("phantomjs")
if not phantomjs:
    message("phantomjs not found")
nodejs = find_which("node") or find_which("nodejs")
if not nodejs:
    message("node/nodejs not found")
# check for puppeteer module
if nodejs and not os.path.exists(f"{sys.prefix}/node_modules/puppeteer"):
    message(f"{sys.prefix}/node_modules/puppeteer not found")
    nodejs = None

_methods = (["puppeteer"] if nodejs else []) + (["phantomjs"] if phantomjs else [])

if _methods:
    settings.html.method = _methods[0], DocString(f"HTML rendering method (available: {', '.join(_methods)})")
else:
    settings.html.method = None, DocString(f"No HTML rendering (phantomjs/nodejs not found)")
settings.html.debug  =  False, DocString("enables debugging output from phantomjs and/or puppeteer")

class RenderError(RuntimeError):
    pass

def _render_html(url, dest, width, height, timeout):
    if settings.html.method == "phantomjs":
        script = os.path.join(os.path.dirname(__file__), "html/phantomjs-html-thumbnail.js")
        debugopt = " --debug=true" if settings.html.debug_phantomjs else ""
        cmd = f"QT_QPA_PLATFORM=offscreen {phantomjs}{debugopt} {script} {url} {dest} {width} {height} {timeout}"
    elif settings.html.method == "puppeteer":
        script = os.path.join(os.path.dirname(__file__), "html/puppeteer-html-thumbnail.js")
        cmd = f"NODE_PATH={sys.prefix}/node_modules {nodejs} {script} {url} {dest} {width} {height} {timeout}"
    else:
        raise RenderError("settings.html.method not set")

    # run the command set up
    message(f"running {cmd}")
    try:
        output = subprocess.check_output(cmd, shell=True).decode()
    except subprocess.CalledProcessError as exc:
        output = exc.output.decode()
        debug(f"{cmd}: exit code {exc.returncode}, output: {output}")
        raise RenderError(f"{settings.html.method} error (code {exc.returncode})")

    debug(f"{cmd}: {output}")


class HTMLFile(FileBase):
    def __init__(self, *args, **kw):
        FileBase.__init__(self, *args, **kw)

    def render_html(self, width="99%", context=None, height=None):
        width = width or settings.display.cell_width
        height = height or settings.display.window_height
        url = render_url(self.fullpath)
        html = render_preamble() + render_title(self.title)
        html += """<IFRAME width={width} height={height} src={url}></IFRAME>""".format(**locals())
        return html

    def _render_thumb_impl(self, width=None, height=None, refresh=False, **kw):
        width  = settings.html.get(width=width)
        height = settings.html.get(height=height)

        thumbnail, thumbnail_url, update = self._get_cache_file("html-render", "png",
                                                                keydict=dict(width=width, height=height))

        if update or refresh:
            url = "file://" + os.path.abspath(self.fullpath)
            try:
                _render_html(url, thumbnail, width, height, 200)
            except Exception as exc:
                return render_error(str(exc))

        return imagefile.ImageFile._render_thumbnail(thumbnail, url=render_url(self.fullpath), npix=width) + "\n"


class URL(ItemBase):
    def __init__(self, url):
        super().__init__(url)
        self.url = url

    def render_html(self, width="99%", context=None, height=None):
        width = width or settings.display.cell_width
        height = height or settings.display.window_height
        html = render_preamble() + render_title(self.title)
        html += f"""<IFRAME width={width} height={height} src={self.url}></IFRAME>"""
        return html

    def _render_thumb_impl(self, width=None, height=None, **kw):
        width  = settings.html.get(width=width)
        height = settings.html.get(height=height)
        filename = self.url.replace("/","_").replace(":", "_") + ".png"

        basepath, baseurl = radiopadre.get_cache_dir("./.urls", "html-render")  # fake ".urls" name which will be stripped
        thumbnail = f"{basepath}/{filename}"

        try:
            _render_html(self.url, thumbnail, width, height, 200)
        except Exception as exc:
            return render_error(str(exc))

        return imagefile.ImageFile._render_thumbnail(thumbnail, url=self.url, npix=width) + "\n"
