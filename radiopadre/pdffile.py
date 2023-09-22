import subprocess
import shlex

from radiopadre.file import FileBase
from radiopadre.render import render_url, render_error
from radiopadre import imagefile

class PDFFile(FileBase):
    def __init__(self, *args, **kw):
        FileBase.__init__(self, *args, **kw)

    def render_html(self,**kw):
        return self.render_thumb(**kw)

    def _render_thumb_impl(self, npix=None, refresh=False, **kw):
        thumbnail, thumbnail_url, update = self._get_cache_file("pdf-render", "png")
        npix = npix or 800

        if update or refresh:
            cmd = f"gs -sDEVICE=png16m -sOutputFile={shlex.quote(thumbnail)} -dLastPage=1 -r300 -dDownScaleFactor=4 -dBATCH " + \
                  f"-dNOPAUSE {shlex.quote(self.fullpath)}"
            try:
                cmd = subprocess.run(cmd, check=True, shell=True, capture_output=True)
            except subprocess.CalledProcessError as exc:
                print(f"{cmd} stdout: {exc.stdout.decode()}")
                print(f"{cmd} stderr: {exc.stderr.decode()}")
                return render_error(f"gs error (code {exc.returncode})")

        return imagefile.ImageFile._render_thumbnail(thumbnail, url=render_url(self.fullpath), npix=npix) + "\n"
