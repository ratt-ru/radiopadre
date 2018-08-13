import astropy.io.fits as pyfits
import traceback
import os, os.path
from IPython.display import HTML, display, Javascript
import matplotlib.pyplot as plt
import matplotlib.colors
import uuid
from collections import OrderedDict

import radiopadre
import radiopadre.file
from radiopadre.render import rich_string, render_title, render_table

from radiopadre import js9, settings

def read_html_template(filename, subs):
    js9_source = os.path.join(js9.DIRNAME, filename)
    with open(js9_source) as inp:
        return inp.read().format(**subs)



class FITSFile(radiopadre.file.FileBase):
    FITSAxisLabels = dict(STOKES=["I", "Q", "U", "V", "YX", "XY", "YY", "XX",
                                  "LR", "RL", "LL", "RR"],
                          COMPLEX=["real", "imag", "weight"])

    def __init__(self, *args, **kw):
        radiopadre.file.FileBase.__init__(self, *args, **kw)
        self._ff = self._header = self._shape = self._image_data = None
        self._rms = {}

    @property
    def fitsobj(self):
        if not self._ff or self.is_updated():
            self._ff = pyfits.open(self.fullpath)
            self.update_mtime()
            self._rms = {}
        return self._ff

    @property
    def header(self,xxx=None):
        return self.fitsobj[0].header

    @property
    def shape(self):
        if self._shape is None:
            hdr = self.header
            self._shape = [ hdr["NAXIS%d" % i] for i in range(1, hdr["NAXIS"] + 1)]
        return self._shape

    @property
    def info(self):
        return self.summary

    def _get_summary_items(self, showpath=False):
        """
        Helper method employed by summary() and _html_summary()
        :return: tuple of name, size, resolution, axes, mod date
        """
        name = self.path if showpath else self.name
        size = resolution = axes = "?"
        try:
            hdr = self.header
            naxis = hdr.get("NAXIS")
            size = "&times;".join(
                [str(hdr.get("NAXIS%d" % i)) for i in range(1, naxis + 1)])
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

    @property
    def summary(self):
        data = [ self._get_summary_items() ]
        preamble = OrderedDict()
        postscript = OrderedDict()
        div_id = uuid.uuid4().hex
        actions = [ self._action_buttons_(preamble=preamble, postscript=postscript, div_id=div_id) ]
        return rich_string(" ".join(map(str,data[0])),
                    render_table(data, html=("size", "axes", "res"), labels=("name", "size", "res", "axes", "modified"),
                                     header=False, numbering=False, actions=actions,
                                     preamble=preamble, postscript=postscript, div_id=div_id))

    def _repr_html_(self):
        return self.summary._repr_html_()

    @staticmethod
    def _html_summary(fits_files, title=None, showpath=False, **kw):
        if not fits_files:
            return "0 files"
        html = render_title(title) if title else ""
        data = [ ff._get_summary_items() for ff in fits_files ]
        preamble = OrderedDict()
        postscript = OrderedDict()
        div_id = uuid.uuid4().hex
        actions = [ df._action_buttons_(preamble=preamble, postscript=postscript, div_id=div_id) for df in fits_files ]
        html += render_table(data, html=("size", "axes", "res"), labels=("name", "size", "res", "axes", "modified"),
                             actions=actions,
                             preamble=preamble, postscript=postscript, div_id=div_id)
        return html

    @staticmethod
    def _show_summary(fits_files, **kw):
        display(HTML(FITSFile._html_summary(fits_files, **kw)))

    @staticmethod
    def _show_thumbs(fits_files,
                     width=None,
                     ncol=None,
                     maxwidth=None,
                     mincol=None,
                     maxcol=None,
                     title=None,
                     fs='small',
                     showpath=False,
                     **kw):
        if not fits_files:
            return None
        if title:
            display(HTML(radiopadre.render_title(title)))
        nrow, ncol, width = radiopadre.file.compute_thumb_geometry(len(fits_files),
                                                                   ncol, mincol,
                                                                   maxcol, width,
                                                                   maxwidth)
        plt.figure(figsize=(width * ncol, width * nrow), dpi=settings.PLOT.SCREEN_DPI)
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
        vmin = settings.FITS.get(VMIN=vmin)
        vmax = settings.FITS.get(VMAX=vmax)
        cmap = settings.FITS.get(COLORMAP=colormap)
        scale = settings.FITS.get(SCALE=scale)
        if scale == 'linear':
            norm = None
        elif scale == 'log':
            norm = matplotlib.colors.SymLogNorm(vmin, vmax)
        else:
            raise ValueError("unknown scle setting'{}'", scale)

        if unroll is None:
            # show single image
            fig = make_figure and plt.figure(figsize=(width, width),
                                             dpi=settings.PLOT.SCREEN_DPI)
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
            plt.figure(figsize=(width * ncol, width * nrow), dpi=settings.PLOT.SCREEN_DPI)
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

    def _make_js9_dual_window_script(self, subs):
        # creates an HTML script per each image, by replacing various arguments in a templated bit of html
        cachedir = radiopadre.get_cache_dir(self.fullpath, "js9-launch")
        symlink = "{}/{}".format(cachedir, self.name)
        if not os.path.exists(symlink):
            os.symlink(os.path.abspath(self.fullpath), symlink)
        js9_target = "{}/{}.{}.{}".format(cachedir, self.basename, "dual", js9.JS9_SCRIPT_SUFFIX)

        # make dict of substitutions for HTML scripts
        subs['fits_image_path'] = self.fullpath
        subs['fits_image_url'] = js9.JS9_FITS_PREFIX_HTTP + self.fullpath
        # subs['lib_scripts'] = open(os.path.join(js9.DIRNAME, "js9-radiopadre.js")).read()
        subs['xsize'], subs['ysize'] = self.shape[:2]
        subs['bin'] = 4
        subs.update(**locals())

        with open(js9_target, 'w') as outp:
            outp.write(read_html_template("js9-window-head-template.html", subs))
            outp.write(read_html_template("js9-dualwindow-geometry-template.html", subs))
            outp.write(read_html_template("js9-dualwindow-body-template.html", subs))
            outp.write(read_html_template("js9-dualwindow-tail-template.html", subs))

        return js9_target

    # def js9_iframe(self):
    #     js9_target = self._make_js9_window_script(subset=True)
    #
    #     return display(HTML('''
    #        <iframe src="{}{}" width=1100 height=780></iframe>
    #        '''.format(js9.JS9_SCRIPT_PREFIX_HTTP, js9_target)))

    def js9_external(self):
        display_id = uuid.uuid4().hex
        # print('Display id = {}'.format(display_id))

        # make dict of substitutions for HTML scripts
        subs = globals().copy()
        subs.update(**locals())
        subs['fits_image_path'] = self.fullpath
        subs['fits_image_url'] = js9.JS9_FITS_PREFIX_JUP + self.fullpath
        subs['fits2fits_options_rebin'] = "fits2fits:true,xcen:2048,ycen:2048,xdim:4096,ydim:4096,bin:'4a'"

        code = read_html_template("js9-dualwindow-body-template.html", subs)

        code += """
            <link type='text/css' rel='stylesheet' href='{js9.JS9_INSTALL_PREFIX_JUP}/js9support.css'>
            <link type='text/css' rel='stylesheet' href='{js9.JS9_INSTALL_PREFIX_JUP}/js9.css'>
            
            <script type="text/javascript">
            // register partner displays
            JS9p.register_partners('rebin-{display_id}-JS9', 'zoom-{display_id}-JS9');
        
            // preload the image
            JS9.Load("{fits_image_path}",
                     {{ {fits2fits_options_rebin},
                        onload: function(im){{
                            console.log("loaded image is", im);
                            JS9.AddRegions({init_zoom_box},
                                           {{color:"red",data:"zoom_region",rotatable:false,removable:false}},
                                           {{display:"rebin-{display_id}-JS9"}});
                        }},
                        zoom:'T'}},
                     {{display:"rebin-{display_id}-JS9"}});
            </script>
        """

        # print code
        display(HTML(code))

    def js9(self):
        display_id = uuid.uuid4().hex
        # print('Display id = {}'.format(display_id))

        # make dict of substitutions for HTML scripts
        subs = globals().copy()
        subs.update(**locals())
        subs['fits_image_url'] = js9.JS9_FITS_PREFIX_JUP + self.fullpath
        subs['fits2fits_options'] = "{fits2fits:false}"

        code = """
            <link type='text/css' rel='stylesheet' href='{js9.JS9_INSTALL_PREFIX_JUP}/js9support.css'>
            <link type='text/css' rel='stylesheet' href='{js9.JS9_INSTALL_PREFIX_JUP}/js9.css'>
        """.format(**subs)

        code += read_html_template("js9-singlewindow-body-template.html", subs)

        code += """
            <script type="text/javascript">
            JS9.AddDivs("{display_id}-JS9");
            JS9.Load("{fits_image_url}", {fits2fits_options},
                     {{display:"{display_id}-JS9"}});
            </script>
        """.format(**subs)

        # print code
        display(HTML(code))

    def _action_buttons_(self, preamble=OrderedDict(), postscript=OrderedDict(), div_id=""):
        """Renders JS9 buttons for image
        """
        subs = globals().copy()
        subs.update(display_id=div_id, **locals())
        subs['fits_image_url'] = js9.JS9_FITS_PREFIX_HTTP + self.fullpath

        if "JS9" not in postscript:
            subs1 = subs.copy()
            # work out layout geometry
            total_width = 900       # TODO: work this out auto-magically from JS one day
            subs1.update(init_style= "display:none",
                         total_width = total_width)
            postscript["JS9"] = read_html_template("js9-dualwindow-inline-geometry-template.html", subs1) + \
                                read_html_template("js9-dualwindow-body-template.html", subs1) + \
                """<script type='text/javascript'>
                        JS9p._pd_{display_id} = new JS9pPartneredDisplays('{display_id}', {settings.FITS.MAX_JS9_SLICE})
                """.format(**subs1)
            if settings.FITS.VMIN:
                postscript["JS9"] += "JS9p._pd_{display_id}.default_vmin = {settings.FITS.VMIN}\n".format(**subs1)
            if settings.FITS.VMAX:
                postscript["JS9"] += "JS9p._pd_{display_id}.default_vmax = {settings.FITS.VMAX}\n".format(**subs1)
            if settings.FITS.COLORMAP:
                postscript["JS9"] += "JS9p._pd_{display_id}.default_colormap = '{settings.FITS.COLORMAP}'\n".format(**subs1)
            if settings.FITS.SCALE:
                postscript["JS9"] += "JS9p._pd_{display_id}.default_scale = '{settings.FITS.SCALE}'\n".format(**subs1)
            postscript["JS9"] += "</script>"

        # use empty display ID for scripts in separate documents
        subs1 = subs.copy()
        subs1['init_style'] = ''
        subs1['display_id'] = ''
        js9_target3 = self._make_js9_dual_window_script(subs1)

        xsize, ysize = self.shape[:2]
        bin = 4
        subs.update(**locals())

        code = """
            <button onclick="JS9p._pd_{display_id}.loadImage('{self.fullpath}', {xsize}, {ysize}, {bin}, true, false)">&#8595;JS9</button>
            <button onclick="window.open('{js9.JS9_SCRIPT_PREFIX_HTTP}{js9_target3}', '_blank')">&#8663;JS9</button>
        """.format(**subs)
        return code
