import astropy.io.fits as pyfits
import traceback
import os, os.path
from IPython.display import HTML, display, Javascript
import matplotlib.pyplot as plt
import matplotlib.colors
import uuid
import math
from collections import OrderedDict

import radiopadre
import radiopadre.file
from radiopadre.render import rich_string, render_title, render_table

from radiopadre import js9, settings
from radiopadre.textfile import NumberedLineList

def read_html_template(filename, subs):
    js9_source = os.path.join(js9.DIRNAME, filename)
    with open(js9_source) as inp:
        return inp.read().format(**subs)


def dict_to_js(dd):
    """Converts a dict object to Javascript source"""
    js = "{"
    for name, value in dd.items():
        if value is None:
            value = "null"
        elif type(value) is bool:
            value = "true" if value else "false"
        elif type(value) is int or type(value) is float:
            value = str(value)
        elif type(value) is str:
            value = "'{}'".format(value)
        else:
            raise TypeError,"can't convert value of type {} to Javascript".format(type(value))
        js += "{}: {},".format(name, value)
    js += "}"
    return js


class FITSFile(radiopadre.file.FileBase):
    FITSAxisLabels = dict(STOKES=["I", "Q", "U", "V", "YX", "XY", "YY", "XX",
                                  "LR", "RL", "LL", "RR"],
                          COMPLEX=["real", "imag", "weight"])

    def __init__(self, *args, **kw):
        self._header = self._hdrobj = self._shape = self._image_data = None
        radiopadre.file.FileBase.__init__(self, *args, **kw)

    @property
    def fitsobj(self):
        return pyfits.open(self.fullpath)

    @property
    def hdrobj(self):
        """Returns the FITS header object"""
        if not self._hdrobj or self.is_updated():
            self._hdrobj = self.fitsobj[0].header
            self.update_mtime()
        return self._hdrobj

    @property
    def header(self):
        """Returns the FITS header object as a rich string"""
        if not self._header or self.is_updated():
            lines = [x.strip() for x in repr(self.hdrobj).split("\n")]
            self._header = NumberedLineList(enumerate(lines), title=self.title + " FITS header")
        return self._header

    @property
    def shape(self):
        if self._shape is None:
            hdr = self.hdrobj
            self._shape = [ hdr["NAXIS%d" % i] for i in range(1, hdr["NAXIS"] + 1)]
        return self._shape

    def _get_summary_items(self, showpath=False):
        """
        Helper method employed by summary() and _html_summary()
        :return: tuple of name, size, resolution, axes, mod date
        """
        name = self.path if showpath else self.name
        size = resolution = axes = "?"
        extensions = False
        try:
            hdr = self.hdrobj
            extensions = hdr.get("EXTEND", 'F') == 'T'
            naxis = hdr.get("NAXIS")
            if naxis:
                size = "&times;".join([str(hdr.get("NAXIS%d" % i)) for i in range(1, naxis + 1)])
                if extensions:
                    size += "+EXT"
            else:
                size = "FITS EXT" if size else ""
            axes = ",".join(
                [hdr.get("CTYPE%d" % i, "?").split("-", 1)[0] for i in range(1, naxis + 1)])
            delt = [abs(hdr.get("CDELT%d" % i, 0)) for i in (1, 2)]
            resolution = []
            if all(delt):
                if delt[0] == delt[1]:
                    delt = [delt[0]]
                for d in delt:
                    if d >= 1:
                        resolution.append("%.2f&deg;" % d)
                    elif d >= 1 / 60.:
                        resolution.append("%.2f'" % (d * 60))
                    elif d >= 1 / 3600:
                        resolution.append("%.2f\"" % (d * 3600))
                    else:
                        resolution.append("%.2g\"" % (d * 3600))
            resolution = "&times;&deg;".join(resolution)
        except:
            traceback.print_exc()
        return name, size, resolution, axes, self.mtime_str

    def _scan_impl(self):
        radiopadre.file.FileBase._scan_impl(self)
        data = [ list(self._get_summary_items()) ]
        preamble = OrderedDict()
        postscript = OrderedDict()
        div_id = uuid.uuid4().hex
        actions = [ self._action_buttons_(preamble=preamble, postscript=postscript, div_id=div_id) ]
        self.size = rich_string(data[0][1].replace("&times;", "x"), data[0][1])
        data[0][0] += ":"
        self.summary = rich_string(" ".join(map(str,data[0])),
                                   render_table(data, html=("size", "axes", "res"), labels=("name", "size", "res", "axes", "modified"),
                                        styles=dict(name="font-weight: bold"),
                                        header=False, numbering=False, actions=actions,
                                        preamble=preamble, postscript=postscript, div_id=div_id))
        data[0] = data[0][1:]
        self.description = rich_string(" ".join(map(str,data[0])),
                                render_table(data, html=("size", "axes", "res"), labels=("size", "res", "axes", "modified"),
                                     header=False, numbering=False, actions=actions,
                                     preamble=preamble, postscript=postscript, div_id=div_id))


    @staticmethod
    def _html_summary(fits_files, title=None, primary_sort="", sort_arrow="", **kw):
        if not fits_files:
            return ""
        html = render_title(title) if title else ""
        data = [ ff._get_summary_items() for ff in fits_files ]
        preamble = OrderedDict()
        postscript = OrderedDict()
        div_id = uuid.uuid4().hex
        html += """<span style="display:inline-block; width: 32px;"></span>""" + \
                FITSFile._collective_action_buttons_(fits_files, preamble, postscript, div_id=div_id)
        actions = [ df._action_buttons_(preamble=preamble, postscript=postscript, div_id=div_id) for df in fits_files ]
        html += render_table(data, html=("size", "axes", "res"),
                             labels=("{}name".format(sort_arrow if primary_sort == "n" else ""),
                                     "{}size".format(sort_arrow if primary_sort == "s" else ""),
                                     "res",
                                     "axes",
                                     "{}modified".format(sort_arrow if primary_sort == "t" else "")),
                             actions=actions,
                             preamble=preamble, postscript=postscript, div_id=div_id)
        return html

    @staticmethod
    def _show_thumbs(fits_files,
                     width=None,
                     ncol=None,
                     maxwidth=None,
                     mincol=None,
                     maxcol=None,
                     title=None,
                     fs='small',
                     max=100,
                     showpath=False,
                     **kw):
        if not fits_files:
            return None
        fits_files = fits_files[:max]
        if title:
            display(HTML(radiopadre.render_title(title)))
        nrow, ncol, width = radiopadre.file.compute_thumb_geometry(len(fits_files),
                                                                   ncol, mincol,
                                                                   maxcol, width,
                                                                   maxwidth)
        plt.figure(figsize=(width * ncol, width * nrow), dpi=settings.plot.screen_dpi)
        for iplot, ff in enumerate(fits_files):
            ax = plt.subplot(nrow, ncol, iplot + 1)
            ax.tick_params(labelsize=kw.get('fs_axis', fs))
            ff.show(index=[0] * 10,
                    unroll=None,
                    filename_in_title=True,
                    make_figure=False,
                    fs_title='small', **kw)

    def show(self,
             index=0,
             xyaxes=(0, 1),
             unroll='STOKES',
             vmin=None,
             vmax=None,
             scale=None,
             colormap=None,
             zoom=None,
             width=None,
             maxwidth=None,
             ncol=None,
             mincol=None,
             maxcol=None,
             fs='medium',
             fs_title=None,
             fs_axis=None,
             fs_colorbar=None,
             colorbar=True,
             make_figure=True,
             filename_in_title=False):
        try:
            ff = self.fitsobj
            hdr = ff[0].header
        except:
            status = "Error reading {}:".format(self.fullpath)
            print status
            traceback.print_exc()
            return status

        # make base slice with ":" for every axis
        naxis = hdr['NAXIS']
        dims = [hdr['NAXIS%d' % i] for i in range(1, naxis + 1)]
        axis_type = [hdr.get("CTYPE%d" % i, str(i))
                     for i in range(1, hdr["NAXIS"] + 1)]
        baseslice = [slice(None)] * hdr['NAXIS']
        # create status string

        status = "%s (%s,%s)" % (self.path, axis_type[xyaxes[0]].split("-")[0],
                                 axis_type[xyaxes[1]].split("-")[0])
        title = self.basename if filename_in_title else ""
        # zoom in if asked
        if zoom:
            x0, y0 = int(dims[xyaxes[0]] / 2), int(dims[xyaxes[1]] / 2)
            xz, yz = int(dims[xyaxes[0]] / (zoom * 2)), int(dims[xyaxes[1]] /
                                                            (zoom * 2))
            xlim = x0 - xz, x0 + xz
            ylim = y0 - yz, y0 + yz
            status += " zoom x%s" % zoom
        else:
            xlim = 0, dims[xyaxes[0]] - 1
            ylim = 0, dims[xyaxes[1]] - 1

        # the set of axes that we need to index into -- remove the XY axes
        # first
        remaining_axes = set(range(naxis)) - set(xyaxes)

        # get axis labels. "1" to "N", unless a special axis like STOKES is
        # used
        axis_labels = {}
        for ax in remaining_axes:
            labels = self.FITSAxisLabels.get(axis_type[ax], None)
            rval, rpix, delt, unit = [hdr.get("C%s%d" % (kw, ax + 1), 1)
                                      for kw in ("RVAL", "RPIX", "DELT", "UNIT")]
            if labels:
                axis_labels[ax] = ["%s %s" %
                                   (axis_type[ax], labels[int(rval - 1 + delt *
                                                              (i + 1 - rpix))])
                                   for i in range(dims[ax])]
            elif unit == 1:
                axis_labels[ax] = ["%s %g" % (axis_type[ax], rval + delt *
                                              (i + 1 - rpix))
                                   for i in range(dims[ax])]
            else:
                axis_labels[ax] = ["%s %g%s" % (axis_type[ax], rval + delt *
                                                (i + 1 - rpix), unit)
                                   for i in range(dims[ax])]

        # is there an unroll axis specified
        if unroll is not None:
            if type(unroll) is str:
                if unroll in axis_type:
                    unroll = axis_type.index(unroll)
                    if dims[unroll] < 2:
                        unroll = None
                else:
                    unroll = None
            if unroll is not None:
                if unroll in remaining_axes:
                    remaining_axes.remove(unroll)
                else:
                    raise ValueError("unknown unroll axis %s" % unroll)

        # we need enough elements in index to take care of the remaining axes
        index = [index] if type(index) is int else list(index)
        for remaxis in sorted(remaining_axes):
            if dims[remaxis] == 1:
                baseslice[remaxis] = 0
            elif not index:
                e = "not enough elements in index to index into axis %s" % \
                    axis_type[remaxis]
                raise TypeError(e)
            else:
                baseslice[remaxis] = i = index.pop(0)
                status += " " + (axis_labels[remaxis][i])
                title += " " + (axis_labels[remaxis][i])
        try:
            data = ff[0].data.T
        except:
            status = "Error reading {}:".format(self.fullpath)
            print status
            traceback.print_exc()
            return status

        # figure out image geometry and make subplots
        nrow, ncol, width = radiopadre.file.compute_thumb_geometry(
            1 if unroll is None else dims[unroll],
            ncol, mincol, maxcol, width, maxwidth)
        vmin = settings.fits.get(vmin=vmin)
        vmax = settings.fits.get(vmax=vmax)
        cmap = settings.fits.get(colormap=colormap)
        scale = settings.fits.get(scale=scale)
        if scale == 'linear':
            norm = None
        elif scale == 'log':
            norm = matplotlib.colors.SymLogNorm(vmin, vmax)
        else:
            raise ValueError("unknown scle setting'{}'", scale)

        if unroll is None:
            # show single image
            fig = make_figure and plt.figure(figsize=(width, width),
                                             dpi=settings.plot.screen_dpi)
            if fig:
                plt.suptitle(self.basename)
            plt.imshow(data[tuple(baseslice)].T, vmin=vmin, vmax=vmax, cmap=cmap, norm=norm)
            if colorbar:
                cbar = plt.colorbar()
                cbar.ax.tick_params(labelsize=fs or fs_colorbar)
            plt.xlabel(axis_type[xyaxes[0]], fontsize=fs or fs_axis)
            plt.ylabel(axis_type[xyaxes[1]], fontsize=fs or fs_axis)
            plt.title(title, fontsize=fs or fs_title)
            fig and fig.axes[0].tick_params(labelsize=fs or fs_axis)
            plt.xlim(*xlim)
            plt.ylim(*ylim)
        else:
            status += ", unrolling " + axis_type[unroll]
            nrow, ncol, width = radiopadre.file.compute_thumb_geometry(dims[unroll],
                                                                       ncol, mincol,
                                                                       maxcol, width,
                                                                       maxwidth)
            plt.figure(figsize=(width * ncol, width * nrow), dpi=settings.plot.screen_dpi)
            plt.suptitle(self.basename)
            for iplot in range(dims[unroll]):
                ax = plt.subplot(nrow, ncol, iplot + 1)
                ax.tick_params(labelsize=fs or fs_axis)
                baseslice[unroll] = iplot
                plt.imshow(data[tuple(baseslice)].T, vmin=vmin, vmax=vmax,
                           cmap=cmap, norm=norm)
                plt.title(title + " " + axis_labels[unroll][iplot],
                          fontsize=fs or fs_title)
                plt.xlabel(axis_type[xyaxes[0]], fontsize=fs or fs_axis)
                plt.ylabel(axis_type[xyaxes[1]], fontsize=fs or fs_axis)
                if colorbar:
                    cbar = plt.colorbar()
                    cbar.ax.tick_params(labelsize=fs or fs_colorbar)
                plt.xlim(*xlim)
                plt.ylim(*ylim)
        return status

    def _make_cache_symlink(self):
        """Makes a symlink from the cache directory to the FITS file. Needed for JS9 to load it."""
        cachedir, cachedir_url = radiopadre.get_cache_dir(self.fullpath, "js9-launch")
        symlink = "{}/{}".format(cachedir, self.name)
        if not os.path.exists(symlink):
            os.symlink(os.path.abspath(self.fullpath), symlink)
        return "{}/{}".format(cachedir_url, self.name)

    def _make_js9_launch_command(self, display_id):
        """Internal method: formats up Javascript statement to load the image into a JS9pPartneredDisplay"""
        xsize, ysize = self.shape[:2]
        bin = math.ceil(max(self.shape[:2])/float(settings.fits.js9_preview_size))
        image_link = self._make_cache_symlink()
        return "JS9p._pd_{display_id}.loadImage('{image_link}', {xsize}, {ysize}, {bin}, true);".format(**locals())

    @staticmethod
    def _make_js9_external_window_script(fits_files, basename, subs, **kw):
        # creates an HTML script per each image, by replacing various arguments in a templated bit of html
        cachedir, cachedir_url = radiopadre.get_cache_dir(fits_files[0].fullpath, "js9-launch")
        js9_target = "{cachedir}/js9-{basename}-newtab.html".format(**locals())

        subs['xzoom'] = int(settings.fits.max_js9_slice * settings.display.window_width/float(settings.display.window_height))
        subs['yzoom'] = settings.fits.max_js9_slice
        defaults = dict(**settings.fits)
        for key in defaults.keys():
            if key in kw:
                defaults[key] = kw[key]
        subs['defaults'] = dict_to_js(defaults)

        subs['launch_command'] = "\n".join([f._make_js9_launch_command(subs['display_id']) for f in fits_files if len(f.shape) >= 2])

        with open(js9_target, 'w') as outp:
            outp.write(read_html_template("js9-window-head-template.html", subs))
            outp.write(read_html_template("js9-dualwindow-geometry-template.html", subs))
            outp.write(read_html_template("js9-dualwindow-body-template.html", subs))
            outp.write(read_html_template("js9-dualwindow-tail-template.html", subs))

        return "{cachedir_url}/js9-{basename}-newtab.html".format(**locals())

    @staticmethod
    def _show_js9ext(fits_files, **kw):
        """Opens new window with JS9 display for images"""
        subs = globals().copy()

        subs['init_style'] = ''
        subs['display_id'] = ''
        subs['window_title'] = kw.get("window_title", "JS9: {} images".format(len(fits_files)))
        subs['js9_target'] = FITSFile._make_js9_external_window_script(fits_files, uuid.uuid4().hex, subs, **kw)

        code = """window.open('{js9.JS9_SCRIPT_PREFIX}{js9_target}', '_blank')""".format(**subs)
        display(Javascript(code))

    @staticmethod
    def _show_js9(fits_files, **kw):
        """Displays FITS images in inline window"""
        subs = globals().copy()
        subs.update(**locals())

        subs['display_id'] = uuid.uuid4().hex
        subs['total_width'] = settings.display.cell_width-16  # subtract 16 to avoid horizontal scrollbar

        defaults = dict(**settings.fits)
        for key in defaults.keys():
            if key in kw:
                defaults[key] = kw[key]
        subs['defaults'] = dict_to_js(defaults)

        subs['init_style'] = 'block'
        subs['defaults']    = dict_to_js(defaults)
        subs['launch_command'] = "\n".join([f._make_js9_launch_command(subs['display_id']) for f in fits_files])

        code = read_html_template("js9-dualwindow-inline-geometry-template.html", subs) + \
                            read_html_template("js9-dualwindow-body-template.html", subs) + \
            """<script type='text/javascript'>
                    JS9p._pd_{display_id} = new JS9pPartneredDisplays('{display_id}', {settings.fits.max_js9_slice}, {settings.fits.max_js9_slice})
                    JS9p._pd_{display_id}.defaults = {defaults}
                    {launch_command}
            </script>""".format(**subs)

        display(HTML(code))

    def js9(self, **kw):
        if len(self.shape) < 2:
            return display(HTML("cannot run JS9 on FITS images with NAXIS<2"))
        return FITSFile._show_js9([self], **kw)

    def js9ext(self, **kw):
        if len(self.shape) < 2:
            return display(HTML("cannot run JS9 on FITS images with NAXIS<2"))
        return FITSFile._show_js9ext([self], window_title="JS9: {}".format(self.fullpath), **kw)

    @staticmethod
    def _insert_js9_postscript(postscript, subs):
        """Inserts scripts to support inline JS9 displays"""
        if "JS9" not in postscript:
            subs1 = subs.copy()
            subs1.update(init_style= "display:none",
                         total_width = settings.display.cell_width-16,  # subtract 16 to avoid horizontal scrollbar
                         defaults = dict_to_js(settings.fits))

            postscript["JS9"] = read_html_template("js9-dualwindow-inline-geometry-template.html", subs1) + \
                                read_html_template("js9-dualwindow-body-template.html", subs1) + \
                """<script type='text/javascript'>
                        JS9p._pd_{display_id} = new JS9pPartneredDisplays('{display_id}', {settings.fits.max_js9_slice}, {settings.fits.max_js9_slice})
                        JS9p._pd_{display_id}.defaults = {defaults}
                   </script>
                """.format(**subs1)

    @staticmethod
    def _collective_action_buttons_(fits_files, preamble=OrderedDict(), postscript=OrderedDict(), div_id=""):
        """Renders JS9 buttons for a collection of images"""
        subs = globals().copy()
        subs.update(display_id=div_id, **locals())

        FITSFile._insert_js9_postscript(postscript, subs)

        # use empty display ID for JS9 scripts launched in a new tab
        subs1 = subs.copy()
        subs1['init_style'] = ''
        subs1['display_id'] = ''
        subs1['window_title'] = "JS9: {} images".format(len(fits_files))
        subs['newtab_html'] = FITSFile._make_js9_external_window_script(fits_files, div_id, subs1)

        subs['launch_command'] = "\n".join([f._make_js9_launch_command(div_id) for f in fits_files if len(f.shape) >= 2])

        postscript["JS9_load_all"] = """<script type='text/javascript'>
            JS9p._pd_{display_id}_load_all = function () {{
                {launch_command}
            }}
        </script>""".format(**subs)

        code = """
            <button title="display all images using an inline JS9 window" style="font-size: 0.8em; height=0.8em;"
                    onclick="JS9p._pd_{display_id}_load_all()">&#8595;JS9 all</button>
            <button title="display all images using JS9 in a new browser tab" style="font-size: 0.8em;  height=0.8em;"
                    onclick="window.open('{newtab_html}', '_blank')">&#8663;JS9 all</button>
        """.format(**subs)
        return code

    def _action_buttons_(self, preamble=OrderedDict(), postscript=OrderedDict(), div_id=""):
        """Renders JS9 buttons for image
        """
        # ignore less than 2D images
        if len(self.shape) < 2:
            return None

        subs = globals().copy()
        subs.update(display_id=div_id, **locals())

        FITSFile._insert_js9_postscript(postscript, subs)

        # use empty display ID for JS9 scripts launched in a new tab
        subs1 = subs.copy()
        subs1['init_style'] = ''
        subs1['display_id'] = ''
        subs1['window_title'] = "JS9: {}".format(self.fullpath)
        subs['newtab_html'] = FITSFile._make_js9_external_window_script([self], self.basename, subs1)

        subs['image_id'] = id(self)
        subs['element_id'] = element_id = "{}_{}".format(div_id, id(self))
        subs['launch_command'] = self._make_js9_launch_command(div_id)

        postscript[element_id] = """<script type='text/javascript'>
            JS9p._pd_{element_id}_load = function () {{
                {launch_command}
                document.getElementById("JS9load-{element_id}").innerHTML = "&#x21A1;JS9"
            }}
        </script>""".format(**subs)

        code = """
            <button id="JS9load-{element_id}" title="display using an inline JS9 window" style="font-size: 0.9em;"
                    onclick="JS9p._pd_{element_id}_load()">&#8595;JS9</button>
            <button id="" title="display using JS9 in a new browser tab" style="font-size: 0.9em;"
                    onclick="window.open('{newtab_html}', '_blank')">&#8663;JS9</button>
        """.format(**subs)
        return code
