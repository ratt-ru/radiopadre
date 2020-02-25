import subprocess
import os.path
import traceback

from radiopadre.file import FileBase
from radiopadre.render import render_title, render_url, render_preamble, render_error
from radiopadre import settings
from radiopadre import imagefile

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

    def _render_thumb_impl(self, npix=None, **kw):
        thumbnail, thumbnail_url, update = self._get_cache_file("html-render", "png")
        npix = npix or 800

        if update:
            script = os.path.join(os.path.dirname(__file__), "../html/html-thumbnail.js")
            path = os.path.abspath(self.fullpath)
            cmd = "phantomjs --debug=true {script} file://{path} {thumbnail} {npix} {npix} 200".format(**locals())
            # print "Command is",cmd
            try:
                output = subprocess.check_output(cmd, shell=True)
            except subprocess.CalledProcessError as exc:
                print(f"{cmd}: {exc.output}")
                return render_error(f"phantomjs error (code {exc.returncode})")
            # print "Output was",output

        return imagefile.ImageFile._render_thumbnail(thumbnail, url=render_url(self.fullpath), npix=npix) + "\n"