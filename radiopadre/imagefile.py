import os
import traceback
import PIL.Image
from IPython.display import HTML, Image, display

import radiopadre
import radiopadre.file
from radiopadre.render import render_title, render_url, render_preamble, rich_string
from radiopadre import settings


def _make_thumbnail(image, width):
    thumbdir, thumbdir_url = radiopadre.get_cache_dir(image, "thumbs")
    if thumbdir is None:
        return None, None

    name = "%d.%s" % (width, os.path.basename(image))

    thumb = os.path.join(thumbdir, name)
    thumb_url = os.path.join(thumbdir_url, name)

    # does thumb need to be updated?
    if not os.path.exists(thumb) or os.path.getmtime(thumb) < os.path.getmtime(image):
        # can't write? That's ok too
        if not os.access(thumbdir, os.W_OK) or os.path.exists(thumb) and not os.access(thumb, os.W_OK):
            return None, None
        img = PIL.Image.open(image)
        img.thumbnail((width,int(round(width*(img.height/float(img.width))))), PIL.Image.ANTIALIAS)
        img.save(thumb)
#        if os.system("convert -thumbnail %d %s %s" % (width, image, thumb)):
#            raise RuntimeError("thumbnail convert failed, maybe imagemagick is not installed?")

    return thumb, thumb_url


class ImageFile(radiopadre.file.FileBase):
    @staticmethod
    def _render_thumbs(images, width=None, ncol=None, maxwidth=None, mincol=None,
                       external_thumbs=None,
                       maxcol=None, title="", **kw):

        if not images:
            return ""
        nrow, ncol, width = radiopadre.file.compute_thumb_geometry(
            len(images), ncol, mincol, maxcol, width, maxwidth)
        npix = int(settings.plot.screen_dpi * width)

        # make list of basename, filename  tuples
        filelist = sorted(
            [(os.path.basename(img.fullpath), img.fullpath) for img in images])

        # keep track of thumbnail fails
        nfail = 0

        html = render_preamble() + render_title(title) + \
               """<br>
                      <table style="border: 0px; text-align: left">\n
                      """
        for row in range(nrow):
            html += """<tr style="border: 0px; text-align: left">\n"""
            filelist_row = filelist[row * ncol:(row + 1) * ncol]
            for name, image in filelist_row:
                html += """<td style="border: 0px; text-align: center">"""
                html += "<a href='%s' target='_blank'>%s</a>" % (render_url(image), name)
                html += "</td>\n"
            html += """</tr><tr style="border: 0px; text-align: left">\n"""
            for _, image in filelist_row:
                if external_thumbs is False:
                    thumb = None
                # make thumbnail and record exceptions. Print the first one, as
                # they really shouldn't happen
                else:
                    try:
                        thumb_realfile, thumb = _make_thumbnail(image, npix)
                        if not thumb and external_thumbs:
                            nfail += 1
                    except:
                        if not nfail:
                            traceback.print_exc()
                        nfail += 1
                        thumb = None
                html += """<td style="border: 0px; text-align: left">"""
                if thumb:
                    html += "<a href='%s' target='_blank'><img src='%s' alt='?'></a>" % (
                        render_url(image), render_url(thumb))
                else:
                    html += "<a href='%s' target='_blank'><img src='%s' width=%d alt='?'></a>" % (
                        render_url(image), render_url(image), npix)
                html += "</td>\n"
            html += "</tr>\n"
        html += "</table>"

        if nfail:
            html += "(WARNING: %d thumbnails unexpectedly failed to generate, check console for errors)<br>\n" % nfail

        return html

    @staticmethod
    def _show_thumbs(images, **kw):
        html = ImageFile._render_thumbs(images, **kw)
        display(HTML(html))

    @property
    def thumb(self):
        return ImageFile._render_thumbs([self])

    def render_html(self, *args, **kw):
        return self.thumb

    def show(self, width=None, **kw):
        display(Image(self.fullpath, width=width and width * 100))

    def _scan_impl(self):
        radiopadre.file.FileBase._scan_impl(self)
        img = PIL.Image.open(self.fullpath)
        size = "{} {}&times;{}".format(img.format, img.width, img.height)
        self.size = self.description = rich_string(size.replace("&times;", "x"), size)
