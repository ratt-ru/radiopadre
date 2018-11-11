import os
import time
import math

from IPython.display import display, HTML

import radiopadre
from radiopadre import settings
from radiopadre.render import render_refresh_button
from collections import OrderedDict

class FileBase(object):
    """Base class referring to an abstract datafile. Sets up some standard attributes in the constructor.

    Attributes:
        fullpath:   the full path to the file, e.g. results/dir1/file1.txt
        path:       path to file relative to root padre directory, e.g. dir1/file1.txt
        name:       the filename (os.path.basename(path)), e.g. file1.txt
        ext:        extension with leading dot, e.g. .txt
        basename:   filename sans extension, e.g. file1
        basepath:   path+filename sans extension, e.g. dir1/file1
        mtime:      modification time
        mtime_str:  string version of mtime
        size:       size in bytes
        size_str:   human-readable size string
    """

    _unit_list = zip(['', 'k', 'M', 'G', 'T', 'P'], [0, 0, 1, 2, 2, 2])

    def __init__(self, path, root="", load=False):
        """Construct a datafile and set up standard attributes.
        
        Args:
            path: path to the file
            root: root folder, will be stripped from beginning of file path if not empty
            load: if True, will "load" detailed file content by calling self._load(). The meaning of this depends
                  on the subclass. For example, when a  DataDir loads, it will scan its content. In general,
                  __init__ is meant to be fast, while slower operations are deferred to _load().

        """
        self.fullpath = path
        self._root = root
        if root and path.startswith(root):
            path = path[len(root):]
            if path.startswith("/"):
                path = path[1:]
        self.path = path
        self.name = os.path.basename(self.path)
        self.basepath, self.ext = os.path.splitext(self.path)
        self.basename = os.path.basename(self.basepath)
        self._scan_impl()
        if load:
            self._load()

    def _scan_impl(self):
        """
        "Scans" file, i.e. performs the faster (read disk) operations to get overall file information. This is meant
        to be augmented by subclasses. Default version just gets filesize and mtime.
        """
        self._loaded = False
        self.update_mtime()
        # get filesize
        self.size = os.path.getsize(self.fullpath)
        # human-friendly size
        if self.size > 0:
            exponent = min(int(math.log(self.size, 1024)),
                           len(self._unit_list) - 1)
            quotient = float(self.size) / 1024 ** exponent
            unit, num_decimals = self._unit_list[exponent]
            format_string = '{:.%sf}{}' % (num_decimals)
            self.size_str = format_string.format(quotient, unit)
        else:
            self.size_str = '0'
        self.description = self.size_str


    def _load_impl(self):
        """
        "Loads" file, i.e. performs the slower (read disk) operations to get detailed file information, in preparation.
        For rendering and such. This is meant to be implemented by subclasses. E.g. a DataDir will scan its contents
        properly at this stage, a table will check for rows and columns, etc.
        """
        pass

    def _load(self):
        """Helper method, calls _load_impl() if not already done"""
        if not self._loaded:
            self._loaded = True
            self._load_impl()


    def rescan(self, force=False):
        """
        Rescans content if mtime has been updated, or if force is True.
        """
        if force or self.is_updated():
            self._scan_impl()
            self._load_impl()


    @staticmethod
    def sort_list(filelist, opt="dxnt"):
        """
        Sort a list of FileBase objects by directory first, eXtension, Time, Size, optionally Reverse
        """
        opt = opt.lower()
        # build up order of comparison
        reverse = 'r' in opt
        comparisons = []
        for key in opt:
            if key == "d":
                comparisons.append(FileBase._sort_directories_first)
            else: 
                attr = FileBase._sort_attributes.get(key)
                if attr:
                    comparisons.append(lambda a,b,reverse: FileBase._sort_by_attribute(a, b, attr, reverse))

        def compare(a, b):
            for comp in comparisons:
                result = comp(a, b, reverse)
                if result:
                    return result
            return 0

        return sorted(filelist, cmp=compare)

    @staticmethod
    def _sort_directories_first(a, b, reverse):
        from .datadir import DataDir
        if type(a) is DataDir and type(b) is not DataDir:
            return -1
        elif type(b) is DataDir and type(a) is not DataDir:
            return 1
        else:
            return 0

    @staticmethod
    def _sort_by_attribute(a, b, attr, reverse):
        result = cmp(getattr(a, attr), getattr(b, attr))
        return -result if reverse else result

    _sort_attributes = dict(x="ext", n="basepath", s="size", t="mtime")

    def update_mtime(self):
        """Updates mtime and mtime_str attributes according to current file mtime,
        returns mtime_str"""
        self.mtime = os.path.getmtime(self.fullpath)
        self.mtime_str = time.strftime(settings.gen.timeformat,
                                       time.localtime(self.mtime))
        return self.mtime_str

    def is_updated(self):
        """Returns True if mtime of underlying file has changed"""
        return os.path.getmtime(self.fullpath) > self.mtime

    def __str__(self):
        return self.path

    def _repr_html_(self):
        self._load()
        return self.show() or self.path

    def show(self, *args, **kw):
        self._load()
        print("show", self.path)

    def watch(self, *args, **kw):
        self._load()
        display(HTML(render_refresh_button()))
        return self.show(*args, **kw)

    def _action_buttons_(self, preamble=OrderedDict(), postscript=OrderedDict(), div_id=""):
        """
        Returns HTML code associated with available actions for this file. Can be None.

        :param preamble: HTML code rendered before e.g. list of files. Insert your own
                         as appropriate.
        :param postscript: HTML code rendered after e.g. list of files. Insert your own
                         as appropriate.
        :param div_id:   unique ID corresponding to rendered chunk of HTML code
        :return: HTML code for action buttons, or None
        """
        return None


def autodetect_file_type(path):
    """
    Determines type of given file/directory, and returns appropriate type object.
    """
    from .fitsfile import FITSFile
    from .imagefile import ImageFile
    from .textfile import TextFile
    from .datadir import DataDir

    ext = os.path.splitext(path)[1].lower()
    if os.path.isdir(path):
        return DataDir
    elif ext in [".fits", ".fts"]:
        return FITSFile
    elif ext in [".png", ".jpg", ".jpeg"]:
        return ImageFile
    elif ext in [".txt", ".log"]:
        return TextFile
    return FileBase


def compute_thumb_geometry(N, ncol, mincol, maxcol, width, maxwidth):
    """
    Works out thumbnail geometry.

    Given nfiles thumbsnails to display, how many rows and columns do we need
    to make, and how wide do we need to make the plot?

    args:
         N:  number of thumbnails to display
         ncol: use a fixed number of columns. If 0, uses mincol/maxcol.
         mincol: use a minimum of that many columns, even if N is fewer.
                 If N<mincol, will use mincol columns
         maxcol: use a maximum of that many columns. If 0, makes a single row
                 of N columns.
         width:  if non-zero, fixes width of individual thumbnail, in inches
         maxwidth: if width is 0, uses a width of maxwidth/ncol for each
                   thumbnail

    Returns:
        tuple of nrow, ncol, width
    """
    # figure out number of columns
    if not ncol:
        mincol = mincol or settings.thumb.mincol or 0
        maxcol = maxcol or settings.thumb.maxcol or 8
        ncol = max(mincol, min(maxcol, N))
    # number of rows
    nrow = int(math.ceil(N / float(ncol)))
    # individual thumbnail width
    width = width or ((maxwidth or settings.plot.width or 16) / float(ncol))
    return nrow, ncol, width
