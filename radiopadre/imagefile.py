import os
import traceback

import IPython.display
from IPython.display import HTML, Image, display

import radiopadre
import radiopadre.file


def _make_thumbnail(image, width):
    thumbdir = "%s/radiopadre-thumbnails" % os.path.dirname(image)
    thumb = os.path.join(thumbdir, "%d.%s" % (width, os.path.basename(image)))
    # does thumbdir need to be created?
    if not os.path.exists(thumbdir):
        if not os.access(os.path.dirname(thumbdir), os.W_OK):
            return None
        os.mkdir(thumbdir)
    # does thumb need to be updated?
    if not os.path.exists(thumb) or os.path.getmtime(thumb) < os.path.getmtime(image):
        # can't write? That's ok too
        if not os.access(thumbdir, os.W_OK) or os.path.exists(thumb) and not os.access(thumb, os.W_OK):
            return None
        if os.system("convert -thumbnail %d %s %s" % (width, image, thumb)):
            raise RuntimeError, "thumbnail convert failed, maybe imagemagick is not installed?"
    return thumb


class ImageFile(radiopadre.file.FileBase):

    @staticmethod
    def _show_thumbs(images, width=None, ncol=None, maxwidth=None, mincol=None,
                     external_thumbs=None,
                     maxcol=None, title=None, **kw):

        if not images:
            return None
        nrow, ncol, width = radiopadre.file.compute_thumb_geometry(len(images), ncol,
                                                              mincol, maxcol,
                                                              width, maxwidth)
        npix = int(radiopadre.DPI * width)

        # make list of basename, filename  tuples
        filelist = sorted(
            [(os.path.basename(img.fullpath), img.fullpath) for img in images])

        # keep track of thumbnail fails
        nfail = 0

        html = radiopadre.render_title(title) + \
            """<br>
                   <table style="border: 0px; text-align: left">\n
                   """
        for row in range(nrow):
            html += """<tr style="border: 0px; text-align: left">\n"""
            filelist_row = filelist[row * ncol:(row + 1) * ncol]
            for name, image in filelist_row:
                html += """<td style="border: 0px; text-align: center">"""
                html += "<a href=/files/%s>%s</a>" % (image, name)
                html += "</td>\n"
            html += """</tr><tr style="border: 0px; text-align: left">\n"""
            for _, image in filelist_row:
                if external_thumbs is False:
                    thumb = None
                # make thumbnail and record exceptions. Print the first one, as
                # they really shouldn't happen
                else:
                    try:
                        thumb = _make_thumbnail(image, npix)
                        if not thumb and external_thumbs:
                            nfail += 1
                    except:
                        if not nfail:
                            traceback.print_exc()
                        nfail += 1
                        thumb = None
                html += """<td style="border: 0px; text-align: left">"""
                if thumb:
                    html += "<a href=/files/%s><img src=/files/%s alt='?'></a>" % (
                        image, thumb)
                else:
                    html += "<a href=/files/%s><img src=/files/%s width=%d alt='?'></a>" % (
                        image, image, npix)
                html += "</td>\n"
            html += "</tr>\n"
        html += "</table>"

        if nfail:
            html += "(WARNING: %d thumbnails unexpectedly failed to generate, check console for errors)<br>\n" % nfail

        display(HTML(html))

    def show(self, width=None, **kw):
        display(Image(self.fullpath, width=width and width * 100))
