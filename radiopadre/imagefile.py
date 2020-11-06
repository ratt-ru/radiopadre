from __future__ import division

import os
import PIL.Image
from IPython.display import HTML, Image, display

import radiopadre
import radiopadre.file
from radiopadre.render import render_title, render_url, render_preamble, rich_string, RichString
from radiopadre import settings
from iglesia import message, debug

PIL.Image.MAX_IMAGE_PIXELS = 30000**2

def is_svg_file(imagepath):
    return os.path.splitext(imagepath)[1].lower() == ".svg"

def _mtime(mtime):
    """
    Sticks mtime into URL, to force a reload of cache if the file has changed.
    Since this breaks nbconvert, we omit it in that mode.
    """
    if radiopadre.NBCONVERT:
        return ""
    else:
        return f"?mtime={mtime}"

def _make_thumbnail(image, width):
    thumbdir, thumbdir_url = radiopadre.get_cache_dir(image, "thumbs")
    if thumbdir is None:
        return None, None

    name = "%d.%s" % (width, os.path.basename(image))

    thumb = os.path.join(thumbdir, name)
    thumb_url = os.path.join(thumbdir_url, name)

    # does thumb need to be updated?
    img_mtime = os.path.getmtime(image)
    thumb_mtime = os.path.getmtime(thumb) if os.path.exists(thumb) else 0
    if thumb_mtime < img_mtime:
        #debug(f"updating thumbnail {thumb} (out of date by {img_mtime-thumb_mtime}s)")
        # can't write? That's ok too
        if not os.access(thumbdir, os.W_OK) or os.path.exists(thumb) and not os.access(thumb, os.W_OK):
            return None, None
        try:
            img = PIL.Image.open(image)
            img.thumbnail((width,int(round(width*(img.height/float(img.width))))), PIL.Image.ANTIALIAS)
        except Exception as exc:
            print(f"Error generating thumbnail for {image}: {exc}")
            return None, None
        
        img.save(thumb)
#        print "rendered thumb", thumb

    thumb_url += _mtime(os.path.getmtime(thumb))

    #        if os.system("convert -thumbnail %d %s %s" % (width, image, thumb)):
#            raise RuntimeError("thumbnail convert failed, maybe imagemagick is not installed?")

    return thumb, thumb_url

class ImageFile(radiopadre.file.FileBase):

    # @staticmethod
    # def _show_thumbs(images, title='', showpath=False, **kw):
    #     if images:
    #         images[0].message("Rendering thumbnails, please wait...", timeout=0)
    #         filelist = [(img.fullpath if showpath else os.path.basename(img.fullpath),
    #                      img.fullpath, render_url(img.fullpath)) for img in images]
    #         html = render_thumbs(filelist, **kw)
    #         images[0].clear_message()
    #         display(HTML(render_preamble() + render_title(title) + html))

    @staticmethod
    def _render_thumbnail(imagepath, url=None, npix=None, mtime=0):
        npix_thumb = settings.thumb.width or settings.display.cell_width // settings.thumb.mincol
        npix = npix or npix_thumb
        url = url or render_url(imagepath)
        if mtime is not None:
            url += _mtime(mtime or os.path.getmtime(imagepath))

        if is_svg_file(imagepath):
            thumb = None    # SVG files rendered natively, no thumbnail needed
        else:
            _, thumb = _make_thumbnail(imagepath, npix_thumb)

        thumb_url = render_url(thumb) if thumb else url

        return f"<a href='{url}' target='_blank'><img src='{thumb_url}' width={npix} alt='?'></a>"

    def _render_thumb_impl(self, npix=None, **kw):
        return ImageFile._render_thumbnail(self.fullpath, npix=npix)

    def render_html(self, **kw):
        return self.render_thumb(**kw)


    def show(self, width=None, **kw):
        display(Image(self.fullpath, width=width and width * 100))


    def _scan_impl(self):
        radiopadre.file.FileBase._scan_impl(self)
        if is_svg_file(self.fullpath):
            self.description = "SVG"
        else:
            try:
                img = PIL.Image.open(self.fullpath)
            except Exception as exc:
                print(f"Error opening image {self.fullpath}: {exc}")
                self.size = self.description = "(error)"
                return
            size = "{} {}&times;{}".format(img.format, img.width, img.height)
            self.size = self.description = rich_string(size.replace("&times;", "x"), size)

#
#
# def render_thumbs(name_path_url,
#                   width=None, ncol=None, maxwidth=None, mincol=None, maxcol=None,
#                   include_titles=True, external_thumbs=None,
#                   action_buttons={}):
#     """
#     Renders a set of thumbnails in a table. Use by both ImageFIle and FITSFile.
#
#     name_path_url is a list of (name, path, url) tuples
#     """
#
#     if not name_path_url:
#         return ""
#     nrow, ncol, width = radiopadre.file.compute_thumb_geometry(
#         len(name_path_url), ncol, mincol, maxcol, width, maxwidth)
#     npix = int(settings.plot.screen_dpi * width)
#
#     # keep track of thumbnail fails
#     nfail = 0
#
#     html = """<table style="border: 0px; text-align: left">\n"""
#     for row in range(nrow):
#         filelist_row = name_path_url[row * ncol:(row + 1) * ncol]
#         if include_titles:
#             html += """<tr style="border: 0px; text-align: left">\n"""
#             for name, image, url in filelist_row:
#                 html += """<td style="border: 0px; text-align: center">"""
#                 if type(name) is RichString:
#                     html += name.html
#                 elif url[0] != '#':
#                     html += "<a href='{}' target='_blank'>{}</a>".format(url, name)
#                 else:
#                     html += name
#                 html += "</td>\n"
#             html += """</tr>\n"""
#         html += """<tr style="border: 0px; text-align: left">\n"""
#         for name, image, url in filelist_row:
#             if url[0] == '#':
#                 html += """<td style="border: 0px; text-align: center">{}</td>""".format(url[1:])
#             else:
#                 if external_thumbs is False:
#                     thumb = None
#                 # make thumbnail and record exceptions. Print the first one, as
#                 # they really shouldn't happen
#                 else:
#                     try:
#                         thumb_realfile, thumb = _make_thumbnail(image, npix)
#                         if not thumb and external_thumbs:
#                             nfail += 1
#                     except:
#                         if not nfail:
#                             traceback.print_exc()
#                         nfail += 1
#                         thumb = None
#                 html += """<td style="border: 0px; text-align: left"><div style="position: relative"><div>"""
#                 mtime = os.path.getmtime(image)
#                 if thumb:
#                     html += "<a href='{}?mtime={}' target='_blank'><img src='{}' alt='?'></a>".format(
#                         url, mtime, render_url(thumb))
#                 else:
#                     html += "<a href='{}?mtime={}' target='_blank'><img src='{}?mtime={}' width={} alt='?'></a>".format(
#                         url, mtime, url, mtime, npix)
#                 if image in action_buttons:
#                     html += """</div><div style="position: absolute; top: 0; left: 0">{}""".format(action_buttons[image])
#                 html += "</div></div></td>\n"
#         html += "</tr>\n"
#     html += "</table>"
#
#     if nfail:
#         html += "(WARNING: %d thumbnails unexpectedly failed to generate, check console for errors)<br>\n" % nfail
#
#     return html
