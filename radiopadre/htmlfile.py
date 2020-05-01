import subprocess
import os.path
import traceback
import radiopadre

from radiopadre.file import FileBase, ItemBase
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

    def _render_thumb_impl(self, width=None, height=None, **kw):
        width  = settings.html.get(width=width)
        height = settings.html.get(height=height)

        thumbnail, thumbnail_url, update = self._get_cache_file("html-render", "png",
                                                                keydict=dict(width=width, height=height))

        if update:
            script = os.path.join(os.path.dirname(__file__), "html/html-thumbnail.js")
            path = os.path.abspath(self.fullpath)
            debug = " --debug=true" if settings.html.debug_phantomjs else ""
            cmd = f"QT_QPA_PLATFORM=offscreen phantomjs{debug} {script} file://{path} {thumbnail} {width} {height} 200"
            # print "Command is",cmd
            try:
                output = subprocess.check_output(cmd, shell=True).decode()
            except subprocess.CalledProcessError as exc:
                output = exc.output.decode()
                # print(f"{cmd}: {output}, code {exc.returncode}")
                return render_error(f"phantomjs error (code {exc.returncode})")
            # print "Output was",output

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

        script = os.path.join(os.path.dirname(__file__), "html/live-html-thumbnail.js")
        cmd = f"phantomjs {script} {self.url} {thumbnail} {width} {height} 200"
        # print "Command is",cmd
        try:
            output = subprocess.check_output(cmd, shell=True).decode()
        except subprocess.CalledProcessError as exc:
            output = exc.output.decode()
            print(f"{cmd}: {output}, code {exc.returncode}")
            return render_error(f"phantomjs error (code {exc.returncode})")
        print("Output was",output)

        return imagefile.ImageFile._render_thumbnail(thumbnail, url=self.url, npix=width) + "\n"
