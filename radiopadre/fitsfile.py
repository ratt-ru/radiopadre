import pyfits
import traceback
from IPython.display import HTML, display
import matplotlib.pyplot as plt

import radiopadre
import radiopadre.file
from radiopadre.render import render_title, render_table


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
        ff = pyfits.open(self.fullpath)
        hdr = ff[0].header

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
        data = ff[0].data.T

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
            plt.imshow(
                data[tuple(baseslice)].T, vmin=vmin, vmax=vmax, cmap=cmap)
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
