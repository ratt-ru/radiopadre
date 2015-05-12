import time
import fnmatch
import os

import astropy

import IPython.display
import IPython.display
from IPython.display import HTML, display

from radiopadre.fitsfile import FITSFile
from radiopadre.imagefile import ImageFile
from radiopadre.file import data_file
from radiopadre.render import render_title, render_table


__version__ = '0.2'

# when running inside a docker containers, these are used to tell radiopadre
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

TWOCOLUMN_LIST_WIDTH = 20  # if all filenames in a list are <= this in length,
# use two columns by default

TIMEFORMAT = "%H:%M:%S %b %d"

astropy.log.setLevel('ERROR')


class FileList(list):
    _sort_attributes = dict(x="ext", n="basename", s="size", t="mtime")

    def __init__(self, files=[], extcol=True, showpath=False,
                 classobj=None, title="",
                 sort="xnt"):
        list.__init__(self, files)
        self._extcol = extcol
        self._showpath = showpath
        self._classobj = classobj
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

    def _repr_html_(self, ncol=None, **kw):
        html = render_title(self._title)
        if not self:
            return html + ": no content"
        # auto-set 1 or 2 columns based on filename length
        if ncol is None:
            max_ = max([len(df.basename) for df in self])
            ncol = 2 if max_ <= TWOCOLUMN_LIST_WIDTH else 1
        if self._extcol:
            labels = "name", "ext", "size", "modified"
            data = [((df.basepath if self._showpath else df.basename), df.ext,
                     df.size_str, df.mtime_str) for df in
                    self]
            links = [(df.path, df.path, None, None) for df in self]
        else:
            labels = "name", "size", "modified"
            data = [((df.basepath if self._showpath else df.basename),
                     df.size_str, df.mtime_str) for df in self]
            links = [(df.path, None, None) for df in self]
        html += render_table(data, labels, links=links, ncol=ncol)
        return html

    def show(self, ncol=None, **kw):
        return IPython.display.display(HTML(self._repr_html_(ncol=ncol, **kw)))

    def list(self, ncol=None, **kw):
        return IPython.display.display(HTML(self._repr_html_(ncol=ncol, **kw)))

    def summary(self, **kw):
        kw.setdefault('title', self._title)
        kw.setdefault('showpath', self._showpath)
        summary = getattr(self._classobj, "_show_summary", None)
        return summary(self, **kw) if summary else self.list(**kw)

    def show_all(self):
        for f in self:
            f.show()

    def __call__(self, pattern):
        files = []
        for patt in pattern.split():
            files += [f for f in self if
                      fnmatch.fnmatch((f.path if self._showpath else f.name),
                                      patt)]
        return FileList(files,
                        extcol=self._extcol, showpath=self._showpath,
                        classobj=self._classobj,
                        title=os.path.join(self._title, pattern))

    def thumbs(self, **kw):
        kw.setdefault('title', self._title)
        kw.setdefault('showpath', self._showpath)
        thumbs = getattr(self._classobj, "_show_thumbs", None)
        return thumbs(self, **kw) if thumbs else None

    def __getslice__(self, *slc):
        return FileList(list.__getslice__(self, *slc),
                        extcol=self._extcol, showpath=self._showpath,
                        classobj=self._classobj,
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
        self.fits = FileList([f for f in self.files if type(f) is FITSFile],
                             classobj=FITSFile,
                             title="FITS files, " + self._title)
        self.images = FileList([f for f in self.files if type(f) is ImageFile],
                               classobj=ImageFile,
                               title="Images, " + self._title)
        self.others = FileList([f for f in self.files
                                if type(f) is not ImageFile and type(
                                    f) is not FITSFile],
                               title="Other files, " + self._title)

    def sort(self, opt):
        for f in self.files, self.fits, self.images:
            f.sort(opt)
        return self

    def show(self):
        return IPython.display.display(self)

    def list(self):
        return IPython.display.display(self)

    def _repr_html_(self):
        return self.files._repr_html_()


class DirList(list):

    def __init__(self, rootfolder=None, include="*.jpg *.png *.fits *.txt",
                 exclude=".* .*/", exclude_empty=True, original_rootfolder=None,
                 title=None, _scan=True):
        """
        Creates a DirList object corresponding to rootfolder and all its
        subdirectories.

        args:
            include: list of filename patterns to include
            exclude: list of filename patterns to exclude. Trailing slash
                matches directory names.
            exclude_empty: if True, directories with no matching files will be
                omitted
            original_rootfolder: the "original" name of rootfolder, used to
                "rewrite" displayed paths when running the notebook in e.g. a
                container (in which case rootfolder refers to the path inside
                the container, while original_rootfolder refers to the true path
                on the host). If None, rootfolder is used
            title: the title of the directory list -- uses
                original_rootfolder or rootfolder by default
            _scan: (for internal use only) if False, directory is not re-scanned
        """
        self._root = rootfolder = rootfolder or os.environ.get(
            'PADRE_DATA_DIR') or os.path.realpath('.')
        self._original_root = original_rootfolder or os.environ.get(
            'PADRE_HOST_DATA_DIR') or rootfolder
        self._title = title or self._original_root

        # setup patterns
        include_files = include.split()
        exclude_files = [f for f in exclude.split() if f[-1] != '/']
        exclude_dirs = [f[:-1] for f in exclude.split() if f[-1] == '/'] + [
            "radiopadre-thumbnails"]
        #
        if _scan:
            for dir_, _, files in os.walk(rootfolder):
                basename = os.path.basename(dir_)
                if any([fnmatch.fnmatch(basename, patt) for patt in
                        exclude_dirs]):
                    continue

                # get files matching include/exclude filters
                files = [f for f in files
                         if any(
                             [fnmatch.fnmatch(f, patt) for patt in include_files])
                         and not any(
                             [fnmatch.fnmatch(f, patt) for patt in exclude_files])]
                if files or not exclude_empty:
                    self.append(DataDir(dir_, files, root=rootfolder,
                                        original_root=original_rootfolder))
        # set up aggregated file lists
        self.files = FileList(title=self._title, showpath=True)
        self.fits = FileList(classobj=FITSFile,
                             title="FITS files, " + self._title, showpath=True)
        self.images = FileList(classobj=ImageFile,
                               title="Images, " + self._title, showpath=True)
        self.others = FileList(title="Other files, " + self._title,
                               showpath=True)
        # init lists
        self._sort()

    def _sort(self):
        self.sort(cmp=lambda x, y: cmp(x.name, y.name))
        # redo lists of files
        for d in self:
            for attr in 'files', 'fits', 'images', 'others':
                getattr(self, attr).extend(getattr(d, attr))

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

    def list(self):
        return IPython.display.display(self)

    def __call__(self, pattern):
        newlist = DirList(self._root, _scan=False, title="%s/%s" % (self._title,
                                                                    pattern))
        for patt in pattern.split():
            newlist += [d for d in self if fnmatch.fnmatch(d.path, patt)]
        newlist._sort()
        return newlist

    def __getslice__(self, *slc):
        newlist = DirList(self._root, _scan=False,
                          title="%s[%s]" % (
                              self._title, ":".join(map(str, slc))))
        newlist += list.__getslice__(self, *slc)
        newlist._sort()
        return newlist
