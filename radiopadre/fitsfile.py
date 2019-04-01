import astropy.io.fits as pyfits
import sys, traceback
import os, os.path
from IPython.display import HTML, display, Javascript
import matplotlib.pyplot as plt
import matplotlib.colors
import uuid
import hashlib
import math
from collections import OrderedDict

import radiopadre
import radiopadre.file
from radiopadre.render import rich_string, render_preamble, render_title, render_table, TransientMessage, render_error

from radiopadre import js9, settings, imagefile
from .textfile import NumberedLineList


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

def dict_to_query(dd):
    """Converts a dict object to URL query string"""
    qs = []
    for name, value in dd.items():
        if value is None:
            value = "null"
        elif type(value) is bool:
            value = "true" if value else "false"
        elif type(value) is int or type(value) is float:
            value = str(value)
        elif type(value) is str:
            value = "{}".format(value)
        else:
            raise TypeError,"can't convert value of type {} to Javascript".format(type(value))
        qs.append("{}={}".format(name, value))
    return "&".join(qs)


class FITSFile(radiopadre.file.FileBase):
    FITSAxisLabels = dict(STOKES=["I", "Q", "U", "V", "YX", "XY", "YY", "XX",
                                  "LR", "RL", "LL", "RR"],
                          COMPLEX=["real", "imag", "weight"])

    def __init__(self, *args, **kw):
        self._header = self._hdrobj = self._shape = self._image_data = self._summary_data = None
        self._png_dir = self._png_url = None
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
        self._summary_data = [ list(self._get_summary_items()) ]
        self._summary = self._description = self._short_summary = None
        radiopadre.file.FileBase._scan_impl(self)

    @property
    def size(self):
        self._setup_summaries()
        return self._size

    @property
    def summary(self):
        self._setup_summaries()
        return self._summary

    @property
    def description(self):
        self._setup_summaries()
        return self._description

    @description.setter
    def description(self, value):
        self._description = rich_string(value)
        self._auto_update_summary()

    @property
    def short_summary(self):
        self._setup_summaries()
        return self._short_summary

    def _setup_summaries(self):
        if self._short_summary is None:
            preamble = OrderedDict()
            postscript = OrderedDict()
            div_id = uuid.uuid4().hex
            actions = [ self._action_buttons_(preamble=preamble, postscript=postscript, div_id=div_id) ]
            self._size = rich_string(self._summary_data[0][1].replace("&times;", "x"), self._summary_data[0][1])
            self._summary_data[0][0] += ":"
            sum = self._summary_data[0]
            self._summary_set = True
            self._summary = rich_string(" ".join(map(str,sum)).replace("&times;", "x"),
                                       render_table(self._summary_data, html=("size", "axes", "res"),
                                            labels=("name", "size", "res", "axes", "modified"),
                                            styles=dict(name="font-weight: bold"),
                                            header=False, numbering=False, actions=actions,
                                            preamble=preamble, postscript=postscript, div_id=div_id))
            ssum = [(sum[0], sum[1])]
            self._short_summary = rich_string(" ".join(map(str, ssum[0])).replace("&times;", "x"),
                                       render_table(ssum, html=("size", "axes", "res"), labels=("name", "size"),
                                            styles=dict(name="font-weight: bold"),
                                            header=False, numbering=False,
                                            div_id=div_id))
            desc = [self._summary_data[0][1:]]
            self._description = rich_string(" ".join(map(str, desc[0])).replace("&times;", "x"),
                                    render_table(desc, html=("size", "axes", "res"), labels=("size", "res", "axes", "modified"),
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
                FITSFile._collective_action_buttons_(fits_files, preamble, postscript, div_id=div_id,
                                                     defaults=FITSFile.make_js9_defaults(**kw))
        actions = [ df._action_buttons_(preamble=preamble, postscript=postscript, div_id=div_id) for df in fits_files ]
        html += render_table(data, html=("size", "axes", "res"),
                             labels=("{}name".format(sort_arrow if primary_sort == "n" else ""),
                                     "{}size".format(sort_arrow if primary_sort == "s" else ""),
                                     "res",
                                     "axes",
                                     "{}modified".format(sort_arrow if primary_sort == "t" else "")),
                             actions=actions,
                             preamble=preamble, postscript=postscript, div_id=div_id)
        #open("tmp-summary.html", "w").write(html)
        return html


    def _return_exception(self, title):
        etype, eval, etb = sys.exc_info()
        display(HTML(render_error("{}: {}".format(title, traceback.format_exception_only(etype, eval)[0]))))
        return NumberedLineList(enumerate(traceback.format_exception(etype, eval, etb)), title=title)


    @staticmethod
    def _show_thumbs(fits_files,
                     width=None, ncol=None, maxwidth=None, mincol=None, maxcol=None,
                     max=100,
                     title='', showpath=False, collective_buttons=True,
                     **kw):
        if fits_files:
            defaults = FITSFile.make_js9_defaults(**kw)

            fits_files[0].message("Rendering FITS thumbnails, please wait...", timeout=0)
            fits_files = fits_files[:max]
            name_image_url = []
            errors = []
            action_buttons = {}

            preamble = OrderedDict()
            postscript = OrderedDict()
            div_id = uuid.uuid4().hex

            for ff in fits_files:
                kw['filename_in_title'] = True
                plots = ff._render_plots(index=[0], showpath=showpath, message=False, **kw)
                # NumberedLineList returned on error, otherwise the normal triplet
                if type(plots) is not NumberedLineList:
                    name_image_url += plots
                    # add action button code keyed on image path
                    for pl in plots:
                        action_buttons[pl[1]] = ff._action_buttons_(preamble=preamble, postscript=postscript,
                                                                    div_id=div_id, defaults=defaults)
                else:
                    errors += errors


            #plt.figure(figsize=(width * ncol, width * nrow), dpi=settings.plot.screen_dpi)
            #for iplot, ff in enumerate(fits_files):
                # ax = plt.subplot(nrow, ncol, iplot + 1)
                # ax.tick_params(labelsize=kw.get('fs_axis', fs))
                # ff._render_plot(index=[0] * 10,
                #         unroll=None,
                #         filename_in_title=True,
                #         make_figure=False,
                #         fs_title='small', **kw)

            fits_files[0].clear_message()

            html = render_preamble() + render_title(title)
            if errors:
                html += "\n".join([err.render_html(full=True) for err in errors])
            if name_image_url:
                if collective_buttons:
                    html += """<span style="display:inline-block; width: 32px;"></span>""" + \
                            FITSFile._collective_action_buttons_(fits_files, preamble, postscript, div_id=div_id,
                                                                 defaults=defaults)
                for code in preamble.values():
                    html += code + "\n"
                html += imagefile.render_thumbs(name_image_url,
                                                width=width, ncol=ncol, maxwidth=maxwidth, mincol=mincol, maxcol=maxcol,
                                                action_buttons=action_buttons)
                for code in postscript.values():
                    html += code + "\n"

            # open("tmp-thumbs.html", "w").write(html)
            display(HTML(html))


    def show(self, **kw):
        FITSFile._show_thumbs([self], ncol=1, mincol=1, maxcol=1, title=None, collective_buttons=False, **kw)


    def _get_png_file(self, keydict={}, **kw):
        """
        Helper method. Returns filename, URL and update status of PNG cache file corresponding to this FITS file, plus
        optional keys (e.g. for axis unrolling).

        Update status is True if FITS file is newer, or PNG file does not exist

        """
        # init paths, if not already done so
        if self._png_dir is None:
            self._png_dir, self._png_url = radiopadre.get_cache_dir(self.fullpath, "fits-render")

        # make name from components
        pngname = ".".join([self.basename] + ["{}-{}".format(*item) for item in keydict.items()] + ["png"])

        pngpath = "{}/{}".format(self._png_dir, pngname)
        update = not os.path.exists(pngpath) or self.mtime > os.path.getmtime(pngpath)

        # check hashes
        if not update:
            checksum = hashlib.md5()
            for key, value in kw.items():
                checksum.update(str(key))
                checksum.update(str(value))
            digest = checksum.digest()
            # check hash file
            hashfile = pngpath + ".md5"
            if not os.path.exists(hashfile) or open(hashfile).read() != digest:
                update = True
                open(hashfile, 'w').write(digest)

        return pngpath, "{}/{}".format(self._png_url, pngname), update


    def _render_plots(self,
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
             fs_title='large',
             fs_axis=None,
             fs_colorbar=None,
             colorbar=True,
             showpath=False,
             refresh=False,             # True to force a re-render
             message=True,              # True to display transient messages
             filename_in_title=False    # True to include filename in plot titles
            ):
        """Renders one or more plots of the FITS file. Returns a list of (name, image, url) tuples,
        or else a NumberedLineList object (as per _return_exception above) if an error is encountered"""
        if message:
            self.message("Reading {}, please wait...".format(self.fullpath), timeout=0)
        try:
            ff = self.fitsobj
            hdr = ff[0].header
            data = ff[0].data
            if data is None:
                return [(self.short_summary, "#no image", "#no image")]
            data = data.T
        except:
            self.clear_message()
            return self._return_exception("Error reading {}:".format(self.fullpath))

        # many things can go wrong during plotting (especially if the data is dodgy, so catch all exceptions
        # here and return them
        try:
            if message:
                self.message("Rendering {}, please wait...".format(self.fullpath), timeout=0)

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
                raise ValueError("unknown scale setting'{}'", scale)

            name_image_url  = []

            if unroll is None:
                # show single image
                image, url, update = self._get_png_file(vmin=vmin, vmax=vmax, cmap=cmap, scale=scale)
                if update or refresh:
                    fig = plt.figure(figsize=(width, width), dpi=settings.plot.screen_dpi)
                    fig.add_axes([0, 0, 1, 1])
                    plt.imshow(data[tuple(baseslice)].T, vmin=vmin, vmax=vmax, cmap=cmap, norm=norm)
                    if colorbar:
                        cbar = plt.colorbar()
                        cbar.ax.tick_params(labelsize=fs_colorbar or fs)
                    plt.xlabel(axis_type[xyaxes[0]], fontsize=fs_axis or fs)
                    plt.ylabel(axis_type[xyaxes[1]], fontsize=fs_axis or fs)
                    plt.title(title, fontsize=fs_title or fs)
                    fig and fig.axes[0].tick_params(labelsize=fs_axis or fs)
                    plt.xlim(*xlim)
                    plt.ylim(*ylim)
                    fig.savefig(image, dpi=settings.plot.screen_dpi, bbox_inches='tight')
#                    print "rendered", image
                    plt.close(fig)
                name_image_url.append((self.short_summary, image, url))
            else:
                status += ", unrolling " + axis_type[unroll]
                nrow, ncol, width = radiopadre.file.compute_thumb_geometry(dims[unroll],
                                                                           ncol, mincol,
                                                                           maxcol, width,
                                                                           maxwidth)
                plt.figure(figsize=(width * ncol, width * nrow), dpi=settings.plot.screen_dpi)
                # plt.suptitle(self.basename)
                for iplot in range(dims[unroll]):
                    image, url, update = self._get_png_file(vmin=vmin, vmax=vmax, cmap=cmap, scale=scale,
                                                            keydict={axis_type[unroll]: iplot})
                    if update or refresh:
                        fig = plt.figure(figsize=(width, width), dpi=settings.plot.screen_dpi)
                        fig.add_axes([0, 0, 1, 1])
                        # ax.tick_params(labelsize=fs_axis or fs)
                        baseslice[unroll] = iplot
                        plt.imshow(data[tuple(baseslice)].T, vmin=vmin, vmax=vmax,
                                   cmap=cmap, norm=norm)
                        plt.title(title + " " + axis_labels[unroll][iplot],
                                  fontsize=fs_title or fs)
                        plt.xlabel(axis_type[xyaxes[0]], fontsize=fs_axis or fs)
                        plt.ylabel(axis_type[xyaxes[1]], fontsize=fs_axis or fs)
                        if colorbar:
                            cbar = plt.colorbar()
                            cbar.ax.tick_params(labelsize=fs_colorbar or fs)
                        plt.xlim(*xlim)
                        plt.ylim(*ylim)
                        fig.savefig(image, dpi=settings.plot.screen_dpi, bbox_inches='tight')
                        plt.close(fig)
                    name_image_url.append((axis_labels[unroll][iplot], image, url))
            self.clear_message()
            return name_image_url
        except:
            self.clear_message()
            return self._return_exception("Error rendering {}:".format(self.fullpath))

    def _make_cache_symlink(self):
        """Makes a symlink from the cache directory to the FITS file. Needed for JS9 to load it."""
        cachedir, cachedir_url = radiopadre.get_cache_dir(self.fullpath, "js9-launch")
        symlink = "{}/{}".format(cachedir, self.name)
        if not os.path.exists(symlink):
            os.symlink(os.path.abspath(self.fullpath), symlink)
        # Cache dir is in the shadow hierarchy, so symlink will always be something like e.g.
        #    /home/user/.radiopadre/home/user/path/to/.radiopadre/js9-launch/x.fits
        # ...and if padre was started in /home/user/path, then jS9helper runs in its shadow equivalent,
        # so what we really want to return is the relative path "to/.radiopadre/js9-launch/x.fits"
        assert symlink.startswith(radiopadre.SHADOW_BASEDIR)
        return symlink[len(radiopadre.SHADOW_BASEDIR)+1:]

    def _make_js9_launch_command(self, display_id):
        """Internal method: formats up Javascript statement to load the image into a JS9pPartneredDisplay"""
        xsize, ysize = self.shape[:2]
        bin = math.ceil(max(self.shape[:2])/float(settings.fits.js9_preview_size))
        image_link = self._make_cache_symlink()
        return "console.log(JS9p,'{image_link}'); JS9p._pd_{display_id}.loadImage('{image_link}', {xsize}, {ysize}, {bin}, true);".format(**locals())

    @staticmethod
    def make_js9_defaults(**kw):
        defaults = dict(**settings.fits)
        for key in defaults.keys():
            if key in kw:
                defaults[key] = kw[key]
        return defaults


    _generated_ext_scripts = set()

    @staticmethod
    def _make_js9_external_window_script(fits_files, basename, subs, defaults={}, single_file=False):
        # creates an HTML script per each image, by replacing various arguments in a templated bit of html
        cachedir, cachedir_url = radiopadre.get_cache_dir(fits_files[0].fullpath, "js9-launch")
        js9_target = "{cachedir}/js9-{basename}-newtab.html".format(**locals())

        skip = single_file and fits_files[0].fullpath in FITSFile._generated_ext_scripts

        if not skip:
            subs['init_defaults'] = dict_to_js(FITSFile.make_js9_defaults())

            ## not really needed
            ## subs['xzoom'] = int(settings.fits.max_js9_slice * settings.display.window_width/float(settings.display.window_height))
            ## subs['yzoom'] = settings.fits.max_js9_slice

            ## print "Making external script {} with defaults {}".format(js9_target, subs['defaults'])

            subs['launch_command'] = "\n".join([f._make_js9_launch_command(subs['display_id']) for f in fits_files if len(f.shape) >= 2])

            with open(js9_target, 'w') as outp:
                outp.write(read_html_template("js9-window-head-template.html", subs))
                outp.write(read_html_template("js9-dualwindow-geometry-template.html", subs))
                outp.write(read_html_template("js9-dualwindow-body-template.html", subs))
                outp.write(read_html_template("js9-dualwindow-tail-template.html", subs))

            if single_file:
                FITSFile._generated_ext_scripts.add(fits_files[0].fullpath)

        defaults_as_query = dict_to_query(defaults)

        return "{cachedir_url}/js9-{basename}-newtab.html?{defaults_as_query}".format(**locals())

    @staticmethod
    def _show_js9ext(fits_files, single_file=False, **kw):
        """Opens new window with JS9 display for images"""
        subs = globals().copy()

        subs['init_style'] = ''
        subs['display_id'] = ''
        subs['window_title'] = kw.get("window_title", "JS9: {} images".format(len(fits_files)))

        subs['js9_target'] = FITSFile._make_js9_external_window_script(fits_files, uuid.uuid4().hex, subs,
                                FITSFile.make_js9_defaults(**kw), single_file=single_file)

        code = """window.open('{js9.JS9_SCRIPT_PREFIX}{js9_target}', '_blank')""".format(**subs)
        display(Javascript(code))

    @staticmethod
    def _show_js9(fits_files, **kw):
        """Displays FITS images in inline window"""
        subs = globals().copy()
        subs.update(**locals())

        subs['display_id'] = uuid.uuid4().hex
        subs['total_width'] = settings.display.cell_width-16  # subtract 16 to avoid horizontal scrollbar
        subs['defaults'] = dict_to_js(FITSFile.make_js9_defaults(**kw))

        subs['init_style'] = 'block'
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
        return FITSFile._show_js9ext([self], single_file=True, window_title="JS9: {}".format(self.fullpath), **kw)

    @staticmethod
    def _insert_js9_postscript(postscript, subs, defaults=None):
        """Inserts scripts to support inline JS9 displays"""
        if "JS9" not in postscript:
            subs1 = subs.copy()
            subs1.update(init_style= "display:none",
                         total_width = settings.display.cell_width-16,  # subtract 16 to avoid horizontal scrollbar
                         defaults=dict_to_js(defaults or FITSFile.make_js9_defaults()))

            postscript["JS9"] = read_html_template("js9-dualwindow-inline-geometry-template.html", subs1) + \
                                read_html_template("js9-dualwindow-body-template.html", subs1) + \
                """<script type='text/javascript'>
                        JS9p._pd_{display_id} = new JS9pPartneredDisplays('{display_id}', {settings.fits.max_js9_slice}, {settings.fits.max_js9_slice})
                        JS9p._pd_{display_id}.defaults = {defaults}
                        JS9p.imageUrlPrefixNative = '/files/'
                   </script>
                """.format(**subs1)

    @staticmethod
    def _collective_action_buttons_(fits_files, preamble=OrderedDict(), postscript=OrderedDict(), div_id="", defaults=None):
        """Renders JS9 buttons for a collection of images"""
        subs = globals().copy()
        subs.update(display_id=div_id, **locals())

        FITSFile._insert_js9_postscript(postscript, subs, defaults=defaults)

        # use empty display ID for JS9 scripts launched in a new tab
        subs1 = subs.copy()
        subs1['init_style'] = ''
        subs1['display_id'] = ''
        subs1['window_title'] = "JS9: {} images".format(len(fits_files))
        subs['newtab_html'] = FITSFile._make_js9_external_window_script(fits_files, div_id, subs1,
                                                                        defaults=defaults or FITSFile.make_js9_defaults())

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

    def _action_buttons_(self, preamble=OrderedDict(), postscript=OrderedDict(), div_id="", defaults=None):
        """Renders JS9 buttons for image
        """
        # ignore less than 2D images
        if len(self.shape) < 2:
            return None

        subs = globals().copy()
        subs.update(display_id=div_id, **locals())

        FITSFile._insert_js9_postscript(postscript, subs, defaults=defaults)

        # use empty display ID for JS9 scripts launched in a new tab
        subs1 = subs.copy()
        subs1['init_style'] = ''
        subs1['display_id'] = ''
        subs1['window_title'] = "JS9: {}".format(self.fullpath)
        # print "making external window script",subs1['defaults']
        subs['newtab_html'] = FITSFile._make_js9_external_window_script([self], self.basename, subs1,
                                                                        defaults=defaults or FITSFile.make_js9_defaults(),
                                                                        single_file=True)

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
