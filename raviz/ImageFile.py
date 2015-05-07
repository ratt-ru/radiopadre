import os

import IPython.display
from IPython.display import HTML, display

import raviz
import raviz.file


class ImageFile(raviz.file.FileBase):
    @staticmethod
    def _show_thumbs(images,
                     width=None,
                     ncol=None,
                     maxwidth=None,
                     mincol=None,
                     maxcol=None,
                     title=None,
                     **kw):

        if not images:
            return None
        nrow, ncol, width = raviz.file.compute_thumb_geometry(len(images), ncol,
                                                              mincol, maxcol,
                                                              width, maxwidth)
        npix = int(raviz.DPI * width)

        # make list of thumbnail,filename pairs
        filelist = [(os.path.basename(img.fullpath),
                     "%s/thumbnails/%d.%s" % (os.path.dirname(img.fullpath),
                                              npix,
                                              os.path.basename(img.fullpath)),
                     img.fullpath)
                    for img in images]
        filelist.sort()

        # (re)generate thumbs if needed
        fails = 0
        for _, thumb, image in filelist:
            if not os.path.exists(os.path.dirname(thumb)):
                if os.system("mkdir %s" % os.path.dirname(thumb)):
                    fails += 1
            if not os.path.exists(thumb) or os.path.getmtime(
                    thumb) < os.path.getmtime(image):
                if os.system("convert -thumbnail %d %s %s" % (
                npix, image, thumb)):
                    fails += 1

        html = raviz.render_title(title) + \
               """<br>
               <table style="border: 0px; text-align: left">\n
               """
        if fails:
            html += "(WARNING: %d thumbnails failed to generate, check console for errors)<br>\n" % fails

        for row in range(nrow):
            html += """<tr style="border: 0px; text-align: left">\n"""
            filelist_row = filelist[row * ncol:(row + 1) * ncol]
            for _, thumb, image in filelist_row:
                html += """<td style="border: 0px; text-align: center">"""
                html += os.path.basename(image)
                html += "</td>\n"
            html += """</tr><tr style="border: 0px; text-align: left">\n"""
            for _, thumb, image in filelist_row:
                html += """<td style="border: 0px; text-align: left">"""
                html += "<a href=%s><img src=%s alt='?'></a>" % (image, thumb)
                html += "</td>\n"
            html += "</tr>\n"
        html += "</table>"

        display(HTML(html))

    def show(self, width=None):
        IPython.display.display(IPython.display.Image(self.fullpath,
                                                      width=width * 100))
