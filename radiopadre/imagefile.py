import os
import traceback
import PIL.Image
from IPython.display import HTML, Image, display

import radiopadre
import radiopadre.file
from radiopadre.render import render_title, render_url, render_preamble, rich_string, RichString
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
#        print "rendered thumb", thumb

    thumb_url += "?mtime={}".format(os.path.getmtime(thumb))

    #        if os.system("convert -thumbnail %d %s %s" % (width, image, thumb)):
#            raise RuntimeError("thumbnail convert failed, maybe imagemagick is not installed?")

    return thumb, thumb_url


class ImageFile(radiopadre.file.FileBase):

    @staticmethod
    def _show_thumbs(images, title='', showpath=False, **kw):
        if images:
            images[0].message("Rendering thumbnails, please wait...", timeout=0)
            filelist = [(img.fullpath if showpath else os.path.basename(img.fullpath),
                         img.fullpath, render_url(img.fullpath)) for img in images]
            html = render_thumbs(filelist, **kw)
            images[0].clear_message()
            display(HTML(render_preamble() + render_title(title) + html))

    @property
    def thumb(self):
        return HTML(self.render_thumb())

    def render_html(self, *args, **kw):
        return self.render_thumb(*args, **kw)

    @staticmethod
    def render_thumbnail(name, imagepath, original_url=None, action_buttons=None, width=None, npix=None, mtime=0):
        html  = """<table style="border: 0px; text-align: left">\n"""
        html += """<tr style="border: 0px; text-align: left">\n"""
        url = render_url(imagepath)
        html += """<td style="border: 0px; text-align: center"><a href='{}' target='_blank'>{}</a></tr>""".\
            format(original_url or url, name)
        html += """</tr><tr style="border: 0px; text-align: left">\n"""

        npix_thumb = int(settings.plot.screen_dpi * (width or settings.plot.width / settings.thumb.maxcol))
        npix = npix or npix_thumb

        thumb_realfile, thumb = _make_thumbnail(imagepath, npix_thumb)

        html += """<td style="border: 0px; text-align: left"><div style="position: relative"><div>"""
        if thumb:
            html += "<a href='{}?mtime={}' target='_blank'><img src='{}' width={} alt='?'></a>".format(
                url, mtime, render_url(thumb), npix)
        else:
            html += "<a href='{}?mtime={}' target='_blank'><img src='{}?mtime={}' width={} alt='?'></a>".format(
                url, mtime, url, mtime, npix)
        if action_buttons:
            html += """<div style="position: absolute; top: 0; left: 0">{}</div>""".format(action_buttons)
        html += "</td></tr>\n"
        html += "</table>"

        return html

    def render_thumb(self, showpath=False, npix=None, width=None, action_buttons=None, *args, **kw):
        name = self.fullpath if showpath else self.basename
        return ImageFile.render_thumbnail(name, self.fullpath, render_url(self.fullpath),
                                                npix=npix, width=width, action_buttons=action_buttons)

    def show(self, width=None, **kw):
        display(Image(self.fullpath, width=width and width * 100))

    def _scan_impl(self):
        radiopadre.file.FileBase._scan_impl(self)
        img = PIL.Image.open(self.fullpath)
        size = "{} {}&times;{}".format(img.format, img.width, img.height)
        self.size = self.description = rich_string(size.replace("&times;", "x"), size)



def render_thumbs(name_path_url,
                  width=None, ncol=None, maxwidth=None, mincol=None, maxcol=None,
                  include_titles=True, external_thumbs=None,
                  action_buttons={}):
    """
    Renders a set of thumbnails in a table. Use by both ImageFIle and FITSFile.

    name_path_url is a list of (name, path, url) tuples
    """

    if not name_path_url:
        return ""
    nrow, ncol, width = radiopadre.file.compute_thumb_geometry(
        len(name_path_url), ncol, mincol, maxcol, width, maxwidth)
    npix = int(settings.plot.screen_dpi * width)

    # keep track of thumbnail fails
    nfail = 0

    html = """<table style="border: 0px; text-align: left">\n"""
    for row in range(nrow):
        filelist_row = name_path_url[row * ncol:(row + 1) * ncol]
        if include_titles:
            html += """<tr style="border: 0px; text-align: left">\n"""
            for name, image, url in filelist_row:
                html += """<td style="border: 0px; text-align: center">"""
                if type(name) is RichString:
                    html += name.html
                elif url[0] != '#':
                    html += "<a href='{}' target='_blank'>{}</a>".format(url, name)
                else:
                    html += name
                html += "</td>\n"
            html += """</tr>\n"""
        html += """<tr style="border: 0px; text-align: left">\n"""
        for name, image, url in filelist_row:
            if url[0] == '#':
                html += """<td style="border: 0px; text-align: center">{}</td>""".format(url[1:])
            else:
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
                html += """<td style="border: 0px; text-align: left"><div style="position: relative"><div>"""
                mtime = os.path.getmtime(image)
                if thumb:
                    html += "<a href='{}?mtime={}' target='_blank'><img src='{}' alt='?'></a>".format(
                        url, mtime, render_url(thumb))
                else:
                    html += "<a href='{}?mtime={}' target='_blank'><img src='{}?mtime={}' width={} alt='?'></a>".format(
                        url, mtime, url, mtime, npix)
                if image in action_buttons:
                    html += """</div><div style="position: absolute; top: 0; left: 0">{}""".format(action_buttons[image])
                html += "</div></div></td>\n"
        html += "</tr>\n"
    html += "</table>"

    if nfail:
        html += "(WARNING: %d thumbnails unexpectedly failed to generate, check console for errors)<br>\n" % nfail

    return html
