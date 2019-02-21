import os
import time
import math

from IPython.display import display, HTML

import radiopadre
from radiopadre import settings
from radiopadre.render import render_refresh_button, rich_string, render_url, TransientMessage
from collections import OrderedDict
from radiopadre import casacore_tables


class ItemBase(object):
    """Base class referring to an abstract displayable data item.


    Properties:
        summary:        short summary of item content
        description:    longer human-readable description (e.g. size, content, etc.)
        title:          displayed title

    """
    def __init__(self, title=None):
        self._summary_set = None
        self._message = None
        self._summary = self._info = self._description = self._size = rich_string(None)
        # use setter method for this, since it'll update the summary
        self.title = title

    def rescan(self, load=False):
        """
        Calling rescan() ensures that the item info is updated from disk.
        If load=True, it is also loaded into memory (i.e. any long I/O deferred from construction time is executed).
        """
        pass

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        self._title = rich_string(value, bold=True)
        self._auto_update_summary()

    @property
    def size(self):
        self.rescan(load=False)
        return self._size

    @size.setter
    def size(self, value):
        self._size = rich_string(value)

    @property
    def description(self):
        self.rescan(load=False)
        return self._description

    @description.setter
    def description(self, value):
        self._description = rich_string(value)
        self._auto_update_summary()

    def _auto_update_summary(self):
        if not self._summary_set:
            self._summary = self._title
            if self._description:
                self._summary = self._summary + rich_string(": {}".format(self._description.text),
                                                            ": {}".format(self._description.html))

    @property
    def summary(self):
        self.rescan(load=False)
        return self._summary or self._title

    @summary.setter
    def summary(self, value):
        self._summary_set = True
        self._summary = rich_string(value)

    @property
    def info(self):
        """info is an alias for summary"""
        self.rescan(load=True)
        return self._info or self._summary or self._title

    @info.setter
    def info(self, value):
        self._info = rich_string(value)

    def __str__(self):
        """str() returns the plain-text version of the file content. Calls self.render_text()."""
        self.rescan()
        return self.render_text()

    def _repr_pretty_(self, p, cycle):
        """
        Implementation for the pretty-print method. Default uses render_text(). Don't want to rescan!
        """
        if not cycle:
            p.text(self.render_text())

    def _repr_html_(self):
        """
        Internal method called by Jupyter to get an HTML rendering of an object.
        Our version makes use of subclass methods, which are mean to implement this behaviour:
        _load() to load content, then _render_html() to render it
        """
        self.rescan()
        self.clear_message()
        return self.render_html()

    def show(self, *args, **kw):
        """
        Renders the object.

        Default version alls _load() to load content, then calls self._render_html(), passing along all arguments,
        then displays the returned HTML using IPython.display
        """
        self.rescan()
        html = self.render_html(*args, **kw)
        self.clear_message()
        display(HTML(html))

    def watch(self, *args, **kw):
        """
        Calls show(), but also renders a refresh button
        """
        display(HTML(render_refresh_button()))
        return self.show(*args, **kw)

    # These methods are meant to be reimplemented by subclasses

    def render_text(self, *args, **kw):
        """
        Method to be implemented by subclasses. Default version falls back to summary().
        :return: plain-text rendering of file content
        """
        return rich_string(self.summary).text

    def render_html(self, *args, **kw):
        """
        Method to be implemented by subclasses. Default version falls back to summary().
        :return: HTML rendering of file content
        """
        return rich_string(self.summary).html

    def _header_text(self, subtitle=None):
        """Helper method, returns standard header line based on title, subtitle and description"""
        if self.title or self.description:
            if self.title:
                return "{}{}: {}\n".format(str(self.title), subtitle or '',self.description)
            else:
                return "{}\n".format(self.description)
        return ""

    def _header_html(self, subtitle=None):
        if self.title or self.description:
            if self.title:
                return "{}{}: {}\n".format(self.title.html, rich_string(subtitle).html, self.description.html)
            else:
                return "{}\n".format(self.description.html)
        return ""

    def message(self, msg, timeout=3, color='blue'):
        """Displays a transient message associated with this object. Timeout=0 for indefinite message.
        Note that show(), above, will clear the message."""
        self.clear_message()
        self._message = TransientMessage(msg, timeout=timeout, color=color)

    def clear_message(self):
        if self._message is not None:
            self._message.hide()
            self._message = None


class FileBase(ItemBase):
    """Base class referring to an abstract datafile. Sets up some standard attributes in the constructor.

    Attributes:
        fullpath:       the full path to the file, e.g. /results/dir1/file1.txt. This is the path used to access
                        the file.
        path:           Display path, used for rendering the file. This could be different from fullpath if
                        e.g. running padre inside a container (in which case fullpath would have had some
                        funny directory prepended to it, which we don't want to show to the user).
                        So e.g. dir1/file1.txt
        name:           the filename (os.path.basename(path)), e.g. file1.txt
        ext:            extension with leading dot, e.g. .txt
        basename:       filename sans extension, e.g. file1
        basepath:       path+filename sans extension, e.g. dir1/file1
        mtime:          modification time
        mtime_str:      string version of mtime
        size:           human-readable size string
        description:    short human-readable description (e.g. size, content, etc.)

        _title:         displayed title (usually same as path, but ./ will be stripped off)
    """

    _unit_list = zip(['', 'k', 'M', 'G', 'T', 'P'], [0, 0, 1, 2, 2, 2])

    @staticmethod
    def get_display_path(path):
        """
        Rewrites path into a display path, taking the rewriting rules (see radiopadre/__init__.py) into
        account
        """
        # strip leading ./
        if path.startswith("./"):
            path = path[2:]
        # use DISPLAY_ROOTDIR if referring to the root directory
        if not path or path == ".":
            return radiopadre.DISPLAY_ROOTDIR
        # if path not fully qualified, use it as is
        if not path.startswith("/"):
            return path
        # if fully qualified, it must start with ABSROOTDIR/
        rootdir = radiopadre.ABSROOTDIR + "/"
        if not path.startswith(rootdir):
            raise RuntimeError("Trying to access {}, which is outside the {} hierarchy".format(path, radiopadre.ROOTDIR))
        # which we strip
        return path[len(rootdir):]


    def __init__(self, path, load=False, title=None):
        """Construct a datafile and set up standard attributes.
        
        Args:
            path: path to the file
            load: if True, will "load" detailed file content by calling self._load(). The meaning of this depends
                  on the subclass. For example, when a  DataDir loads, it will scan its content. In general,
                  __init__ is meant to be fast, while slower operations are deferred to _load().

        """
        self.fullpath = path
        self.path = FileBase.get_display_path(path)
        if title is None:
            if os.path.isdir(self.fullpath):
                title = rich_string(self.path, bold=True)
            else:
                title = rich_string(self.path,
                        "<A HREF='{}' target='_blank'><B>{}</B></A>".format(render_url(self.fullpath), self.path))

        ItemBase.__init__(self, title=title)

        self.name = os.path.basename(self.fullpath)
        self.basepath, self.ext = os.path.splitext(self.path)
        self.basename = os.path.basename(self.basepath)

        # directory key set up for sorting purposes
        # directories sort themselves before files
        isdir = int(os.path.isdir(self.fullpath))
        self._dirkey = 1-isdir, os.path.dirname(self.fullpath)

        self._scan_impl()
        # timestamp of file last time content was loaded
        self._loaded_mtime = None
        if load:
            self._load()

    def _load(self):
        """Helper method, calls _load_impl() if not already done"""
        if self._loaded_mtime is None or self._loaded_mtime < self.mtime:
            self._loaded_mtime = self.mtime
            self._load_impl()

    def rescan(self, force=False, load=True):
        """
        Rescans content if mtime has been updated, or if force is True. If load is True, forces a load as well.
        """
        if force or self.is_updated():
            self._scan_impl()
        if load:
            self._load()

    def update_mtime(self):
        """Updates mtime and mtime_str attributes according to current file mtime,
        returns mtime_str"""
        self.mtime = os.path.getmtime(self.fullpath)
        self.mtime_str = time.strftime(settings.gen.timeformat, time.localtime(self.mtime))
        return self.mtime_str

    def is_updated(self):
        """Returns True if mtime of underlying file has changed since the last scan"""
        return os.path.getmtime(self.fullpath) > self.mtime

    def _scan_impl(self):
        """
        "Scans" file, i.e. performs the faster (read disk) operations to get overall file information. This is meant
        to be augmented by subclasses. Default version just gets filesize and mtime.
        """
        self.update_mtime()
        # get filesize
        size = self._byte_size = os.path.getsize(self.fullpath)
        # human-friendly size
        if size > 0:
            exponent = min(int(math.log(size, 1024)),
                           len(self._unit_list) - 1)
            quotient = float(size) / 1024 ** exponent
            unit, num_decimals = self._unit_list[exponent]
            format_string = '{:.%sf}{}' % (num_decimals)
            self.size = format_string.format(quotient, unit)
        else:
            self.size = '0'
        self.description = rich_string("{} {}".format(self.size, self.mtime_str))

    def _load_impl(self):
        """
        "Loads" file, i.e. performs the slower (read disk) operations to get detailed file information, in preparation.
        For rendering and such. This is meant to be implemented by subclasses. E.g. a DataDir will scan its contents
        properly at this stage, a table will check for rows and columns, etc.
        """
        pass

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


    @staticmethod
    def sort_list(filelist, opt="dxnt"):
        """
        Sort a list of FileBase objects by directory first, eXtension, Time, Size, optionally Reverse
        """
        # build up order of comparison
        comparisons = []
        reverse = 1
        for key in opt:
            if key in 'rR':
                reverse = -1
            else:
                if key.upper() == key:
                    key = key.lower()
                    reverse = -1
                attr = FileBase._sort_attributes.get(key)
                if attr:
                    comparisons.append(lambda a,b,rev=reverse,x=attr: rev*cmp(getattr(a, x), getattr(b, x)))
                reverse = 1

        def compare(a, b):
            for comp in comparisons:
                result = comp(a, b)
                if result:
                    return result
            return 0

        return sorted(filelist, cmp=compare)

    _sort_attributes = dict(d="_dirkey", x="ext", n="basepath", s="_byte_size", t="mtime")


def autodetect_file_type(path):
    """
    Determines type of given file/directory, and returns appropriate type object.
    """
    from .fitsfile import FITSFile
    from .imagefile import ImageFile
    from .textfile import TextFile
    from .datadir import DataDir
    from .casatable import CasaTable
    from .htmlfile import HTMLFile

    if not os.path.exists(path):
        return None

    ext = os.path.splitext(path)[1].lower()
    if os.path.isdir(path):
        if casacore_tables and casacore_tables.tableexists(path):
            return CasaTable
        else:
            return DataDir
    elif ext in [".fits", ".fts"]:
        return FITSFile
    elif ext in [".html" ]:
        return HTMLFile
    elif ext in [".png", ".jpg", ".jpeg"]:
        return ImageFile
    elif ext in [".txt", ".log", ".py", ".sh"]:
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
