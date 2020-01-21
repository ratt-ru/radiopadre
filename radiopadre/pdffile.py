import subprocess

from radiopadre.file import FileBase
from radiopadre.render import render_url, render_error
from radiopadre import imagefile

class PDFFile(FileBase):
    def __init__(self, *args, **kw):
        FileBase.__init__(self, *args, **kw)

    def render_html(self,**kw):
        return self.render_thumb(**kw)

    def _render_thumb_impl(self, npix=None, **kw):
        thumbnail, thumbnail_url, update = self._get_cache_file("pdf-render", "png")
        npix = npix or 800

        if update:
            cmd = "gs -sDEVICE=png16m -sOutputFile={thumbnail} -dLastPage=1 -r300 -dDownScaleFactor=4 -dBATCH " \
                  "-dNOPAUSE {self.fullpath}".format(**locals())
            try:
                output = subprocess.check_output(cmd, shell=True)
            except subprocess.CalledProcessError as exc:
                print(f"{cmd}: {exc.output}")
                return render_error(f"phantomjs error (code {exc.returncode})")

        return imagefile.ImageFile._render_thumbnail(thumbnail, url=render_url(self.fullpath), npix=npix) + "\n"
