import astropy.io.fits as pyfits
import traceback
import os, os.path
from IPython.display import HTML, display
import matplotlib.pyplot as plt

import radiopadre
import radiopadre.file
from radiopadre.render import render_title, render_table

def get_js9_config():
    """This returns the path to the JS9 installation."""

    # method 1. Use separate HTTP server
    port = int(open(os.path.join(radiopadre.ROOTDIR, ".radiopadre", "http_port")).readline().strip())
    return "/.radiopadre/js9", "http://localhost:{}/".format(port), "/", "js9-http.html"

    # method 2: JS9 served through Tornado
    #return "/files/.radiopadre/js9", "/files/", "/files/", "js9-tornado.html"

class FITSFile(radiopadre.file.FileBase):
    FITSAxisLabels = dict(STOKES=["I", "Q", "U", "V", "YX", "XY", "YY", "XX",
                                  "LR", "RL", "LL", "RR"],
                          COMPLEX=["real", "imag", "weight"])

    def __init__(self, *args, **kw):
        radiopadre.file.FileBase.__init__(self, *args, **kw)
        self._ff = self._image_data = None

    def open(self):
        if not self._ff:
            self._ff = pyfits.open(self.fullpath)
        return self._ff

    def info(self):
        hdr = self.open()[0].header
        sizes = [str(hdr["NAXIS%d" % i]) for i in range(1, hdr["NAXIS"] + 1)]
        axes = [hdr.get("CTYPE%d" % i, str(i))
                for i in range(1, hdr["NAXIS"] + 1)]
        print(self.path, "x".join(sizes), ",".join(axes))

    @staticmethod
    def _show_summary(fits_files, title=None, showpath=False):
        if not fits_files:
            display(HTML("0 files"))
            return
        if title:
            display(HTML(render_title(title)))
        data = []
        for ff in fits_files:
            name = ff.path if showpath else ff.name
            size = resolution = axes = "?"
            try:
                hdr = pyfits.open(ff.fullpath)[0].header
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
                            resolution.append("%.1f&deg;" % d)
                        elif d >= 1 / 60.:
                            resolution.append("%.1f'" % (d * 60))
                        else:
                            resolution.append("%.1g\"" % (d * 3600))
                resolution = "&times;&deg;".join(resolution)
            except:
                traceback.print_exc()
            data += [(name, size, resolution, axes, ff.mtime_str)]
        display(HTML(render_table(data,
                                  html=("size", "axes", "res"),
                                  labels=("name", "size", "res", "axes", "modified"))))

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
        plt.figure(figsize=(width * ncol, width * nrow), dpi=radiopadre.DPI)
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
             cmap='cubehelix',
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
            ff = pyfits.open(self.fullpath)
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
                unroll = axis_type.index(
                    unroll) if unroll in axis_type else None
                if dims[unroll] < 2:
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
        if unroll is None:
            # show single image
            fig = make_figure and plt.figure(figsize=(width, width),
                                             dpi=radiopadre.DPI)
            if fig:
                plt.suptitle(self.basename)
            plt.imshow(data[tuple(baseslice)].T, vmin=vmin, vmax=vmax, cmap=cmap)
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
            plt.figure(figsize=(width * ncol, width * nrow), dpi=radiopadre.DPI)
            plt.suptitle(self.basename)
            for iplot in range(dims[unroll]):
                ax = plt.subplot(nrow, ncol, iplot + 1)
                ax.tick_params(labelsize=fs or fs_axis)
                baseslice[unroll] = iplot
                plt.imshow(data[tuple(baseslice)].T, vmin=vmin, vmax=vmax,
                           cmap=cmap)
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

    def _get_js9_script(self):
        # creates an HTML script per each image, by replacing the image name in a template
        cachedir = radiopadre.get_cache_dir(self.fullpath, "js9-launch")

        #        js9link = os.path.join(cachedir, "js9")
        #        if not os.path.exists(js9link):
        #            os.symlink(os.path.dirname(__file__) + "/../js9-www", js9link)

        js9_file_prefix, js9_server_prefix, js9_fits_prefix, js9_target_name = get_js9_config()

        js9_source = os.path.dirname(__file__) + "/html/js9-inline-template.html"
        js9_target = "{}/{}.{}".format(cachedir, self.basename, js9_target_name)

        # what's most recently modified: this radiopadre source, or FITS file
        mtime = max(os.path.getmtime(__file__),
                    os.path.getmtime(js9_source),
                    os.path.getmtime(self.fullpath))

        # refresh the HTML file if this is less recent
        if not os.path.exists(js9_target) or os.path.getmtime(js9_target) < mtime:
            # Long method to 'edit the dom', bs4 prospect
            js9_source = os.path.dirname(__file__) + "/html/js9-inline-template.html"
            with open(js9_source) as inp, open(js9_target, 'w') as outp:
                for line in inp.readlines():
                    # rewrite paths to js9 files
                    line = line.replace('href="', 'href="{}/'.format(js9_file_prefix))
                    line = line.replace('src="', 'src="{}/'.format(js9_file_prefix))
                    # rewrite path to image
                    line = line.replace("PATH_TO_RADIOPADRE_IMAGE", js9_fits_prefix + self.fullpath)
                    outp.write(line)

        return js9_target, js9_server_prefix

    def js9(self):
        js9_target, js9_server_prefix = self._get_js9_script()

        return display(HTML('''
           <iframe src="{}{}" width=1100 height=780></iframe>
           '''.format(js9_server_prefix, js9_target)))

    def _action_buttons_(self):
        """Renders JS9 button for FITS image given by 'imag'"""
        js9_target, js9_server_prefix = self._get_js9_script()

        return """
            <button onclick="window.open('{js9_server_prefix}{js9_target}', '_blank')">&#8599;JS9</button> 
            <script>
                        var loadNewWindow = function (url) {{
                            // alert("opening: "+url);
                            window.open(url,'_blank');
                        }}
            </script>
        """.format(**locals())
