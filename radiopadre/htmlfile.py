import subprocess
import os.path
import sys
import re
import radiopadre

from radiopadre.file import FileBase, ItemBase
from radiopadre.render import render_titled_content, render_url, render_preamble, render_error
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
        cmd = [phantomjs]
        if settings.html.debug:
            cmd.append("--debug=true")
        cmd += [script, url, dest, width, height, timeout]
        env = os.environ.copy()
        env['QT_QPA_PLATFORM'] = 'offscreen'
    elif settings.html.method == "puppeteer":
        script = os.path.join(os.path.dirname(__file__), "html/puppeteer-html-thumbnail.js")
        cmd = [nodejs, script, url, dest, width, height, timeout]
        env = os.environ.copy()
        env['NODE_PATH'] = f"{sys.prefix}/node_modules"
    else:
        raise RenderError("settings.html.method not set")

    error = None
    cmd = list(map(str, cmd))
    # run the command set up
    message(f"running {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as exc:
        result = exc
        error = f"{cmd[0]}: exit code {exc.returncode}"
        debug(error)
    stdout = result.stdout.decode() if result.stdout is not None else None
    stderr = result.stderr.decode() if result.stderr is not None else None
    debug(f"{cmd[0]} stdout: {stdout}; stderr:{stderr}")

    if error:
        raise RenderError(error)


class HTMLFile(FileBase):
    def __init__(self, *args, **kw):
        FileBase.__init__(self, *args, **kw)

    def render_html(self, width="99%", context=None, height=None, title=None, collapsed=None, **kw):
        title_html = self._header_html(title=title)
        if collapsed is None and settings.gen.collapsible:
            collapsed = False

        width = width or settings.display.cell_width
        height = height or settings.display.window_height
        url = render_url(self.fullpath)
        content_html = f"""<IFRAME width={width} height={height} src={url}></IFRAME>"""
        return render_preamble() + \
                render_titled_content(title_html=title_html,
                                      content_html=content_html,
                                      collapsed=collapsed)

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
    def __init__(self, url, title=None):
        super().__init__(title or url)
        self.url = url
        self.fullpath = self.path = url

    def render_html(self, width="99%", context=None, height=None, title=None, collapsed=None, **kw):
        title_html = self._header_html(title=title)
        if collapsed is None and settings.gen.collapsible:
            collapsed = False
        width = width or settings.display.cell_width
        height = height or settings.display.window_height
        content_html = f"""<IFRAME width={width} height={height} src={self.url}></IFRAME>"""
        return render_preamble() + \
                render_titled_content(title_html=title_html,
                                      content_html=content_html,
                                      collapsed=collapsed)

    def _render_thumb_impl(self, width=None, height=None, **kw):
        width  = settings.html.get(width=width)
        height = settings.html.get(height=height)
        delay = kw.get('delay', 200)
        filename = re.sub(r"[/:;&?#]", "_", self.url) + ".png"

        basepath, baseurl = radiopadre.get_cache_dir("./.urls", "html-render")  # fake ".urls" name which will be stripped
        thumbnail = f"{basepath}/{filename}"

        try:
            _render_html(self.url, thumbnail, width, height, delay)
        except Exception as exc:
            return render_error(str(exc))

        return imagefile.ImageFile._render_thumbnail(thumbnail, url=self.url, npix=width, mtime=None) + "\n"
