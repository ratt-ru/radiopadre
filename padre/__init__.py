import os
import time
import fnmatch

import astropy

import IPython.display
import IPython.display
from IPython.display import HTML, display

from padre.fitsfile import FITSFile
from padre.imagefile import ImageFile
from padre.file import data_file
from padre.render import render_title, render_table


__version__ = '0.1'

# when running inside a docker containers, these are used to tell padre
# where the results directory is mounted, and what its original path on 
# the host is. Note that rendered paths will display the _host_ path rather 
# than the internal container path (to avoid confusing the user),
# hence the need to know ORIGINAL_RESULTDIR
RESULTDIR = os.environ.get('PADRE_DATA_DIR', None)
ORIGINAL_RESULTDIR = os.environ.get('PADRE_ORIGINAL_DIR', None)

WIDTH = None  # globally fix a plot width (inches)
MINCOL = 2  # default min # of columns to display in thumbnail view
MAXCOL = 4  # default max # of columns to display in thumbnail view
MAXWIDTH = 16  # default width of thumbnail view (inches)
DPI = 80  # screen DPI

TIMEFORMAT = "%H:%M:%S %b %d"

astropy.log.setLevel('ERROR')


class FileList(list):
    _sort_attributes = dict(x="ext", n="basename", s="size", t="mtime")

    def __init__(self, files=[], extcol=True, thumbs=None, title="",
                 sort="xnt"):
        list.__init__(self, files)
        self._extcol = extcol
        self._thumbs = thumbs
        self._title = title
        if sort:
            self.sort(sort)

    def sort(self, opt="xnt"):
        """
        Sort the filelist by name, eXtension, Time, Size, optionally Reverse
        """
        opt = opt.lower()
        # build up order of comparison
        cmpattr = []
        for attr in opt:
            if attr in self._sort_attributes:
                cmpattr.append(self._sort_attributes[attr])

        def compare(a, b, attrs=cmpattr):
            for attr in attrs:
                result = cmp(getattr(a, attr), getattr(b, attr))
                if result:
                    return result
            return 0

        list.sort(self, cmp=compare, reverse='r' in opt)
        return self

    def _repr_html_(self, ncol=1):
        html = render_title(self._title)
        if self._extcol:
            labels = "name", "ext", "size", "modified"
            data = [(df.basename, df.ext, df.size_str, df.mtime_str) for df in
                    self]
            links = [(df.fullpath, df.fullpath, None, None) for df in self]
        else:
            labels = "name", "size", "modified"
            data = [(df.basename, df.size_str, df.mtime_str) for df in self]
            links = [(df.fullpath, None, None) for df in self]
        html += render_table(data, labels, links=links, ncol=ncol)
        return html

    def show(self, ncol=1):
        return IPython.display.display(HTML(self._repr_html_(ncol=ncol)))

    def show_all(self):
        for f in self:
            f.show()

    def __call__(self, pattern):
        files = [f for f in self if fnmatch.fnmatch(f.name, pattern)]
        return FileList(files,
                        extcol=self._extcol,
                        thumbs=self._thumbs,
                        title=os.path.join(self._title, pattern))

    def thumbs(self, **kw):
        kw['title'] = self._title
        return self._thumbs(self, **kw) if self._thumbs else None

    def __getslice__(self, *slc):
        return FileList(list.__getslice__(self, *slc),
                        extcol=self._extcol,
                        thumbs=self._thumbs,
                        title="%s[%s]" % (self._title, ":".join(map(str, slc))))


class DataDir(object):
    """
    This class represents a directory in the data folder
    """

    def __init__(self, name, files=[], root=".", original_root=None):
        self.fullpath = name
        if root and name.startswith(root):
            name = name[len(root):]
            if name.startswith("/"):
                name = name[1:]
            name = name or "."
        self.name = self.path = name
        self.mtime = os.path.getmtime(self.fullpath)
        files = [f for f in files if not f.startswith('.')]

        # our title, in HTML
        path = self.path if self.path is not "." else ""
        self._title = os.path.join(original_root or root, path)

        # make list of DataFiles and sort by time
        self.files = FileList([data_file(os.path.join(self.fullpath, f),
                                         root=root) for f in files],
                              title=self._title)

        # make separate lists of fits files and image files
        files = [f for f in self.files if type(f) is FITSFile]
        self.fits = FileList(files,
                             extcol=False,
                             thumbs=FITSFile._show_thumbs,
                             title="FITS files, " + self._title)

        self.images = FileList([f for f in self.files
                                if type(f) is ImageFile],
                               extcol=False,
                               thumbs=ImageFile._show_thumbs,
                               title="Images, " + self._title)

    def sort(self, opt):
        for f in self.files, self.fits, self.images:
            f.sort(opt)
        return self

    def show(self):
        return IPython.display.display(self)

    def _repr_html_(self):
        return self.files._repr_html_()


class DirList(list):
    def __init__(self, rootfolder=None, pattern="*", title=None, original_rootfolder=None):
        self._root = rootfolder = rootfolder or os.environ.get('PADRE_DATA_DIR') or os.path.realpath('.')
        self._original_root = original_rootfolder or os.environ.get('PADRE_HOST_DATA_DIR') or rootfolder 
        self._title = title or original_rootfolder
        for dir_, _, files in os.walk(rootfolder):
	        basename = os.path.basename(dir_)
	        if fnmatch.fnmatch(basename,
	                           pattern) and not basename.startswith("."):
	            self.append(DataDir(dir_, files, root=rootfolder, original_root=original_rootfolder))
        self._sort()

    def _sort(self):
        self.sort(cmp=lambda x, y: cmp(x.name, y.name))

    def _repr_html_(self):
        html = render_title(self._title)
        dirlist = []
        for dir_ in self:
            nfits = len(dir_.fits)
            nimg = len(dir_.images)
            nother = len(dir_.files) - nfits - nimg
            dirlist.append(
                (dir_.name, nfits, nimg, nother,
                 time.strftime(TIMEFORMAT, time.localtime(dir_.mtime))))
        html += render_table(dirlist, labels=("name", "# FITS", "# img",
                                              "# others", "modified"))
        return html

    def show(self):
        return IPython.display.display(self)

    def __call__(self, pattern):
        return DirList(self._root, pattern,
                       title=os.path.join(self._title, pattern))

    def __getslice__(self, *slc):
        newlist = DirList(self._root, scan=False,
                          title="%s[%s]" % (self._title,
                                            ":".join(map(str, slc))))
        newlist += list.__getslice__(self, *slc)
        newlist._sort()
        return newlist
