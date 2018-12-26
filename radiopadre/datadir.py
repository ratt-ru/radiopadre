import IPython
from IPython.display import display, HTML, Javascript
import os
import fnmatch
import time

from .file import FileBase, autodetect_file_type
from .filelist import FileList
from .fitsfile import FITSFile
from .imagefile import ImageFile
from .casatable import CasaTable
from .render import render_table, render_preamble, render_refresh_button, rich_string, render_url, render_title

import radiopadre
from radiopadre import settings

# Need a flag raised in show() and other methods which prevents _load_impl() from being invoked.

def _matches(filename, include_patterns=(), exclude_patterns=()):
    """
    Returns True if filename matches a set of include/exclude patterns.
    If include is set, filename MUST be in an include pattern. Filename cannot be in any exclude pattern.
    """
    if include_patterns and not any([fnmatch.fnmatch(filename, patt) for patt in include_patterns]):
        return False
    return not any([fnmatch.fnmatch(filename, patt) for patt in exclude_patterns])

class DataDir(FileList):
    """
    This class represents a directory
    """

    def __init__(self, name,
                 include=None, exclude=None,
                 include_dir=None, exclude_dir=None,
                 include_empty=None, show_hidden=None,
                 sort="dxnt"):
                 # _skip_js_init=False):
        """
        """

        # # make sure Javascript end is initialized
        # self._skip_js_init = _skip_js_init
        # if not _skip_js_init:
        #     radiopadre._init_js_side()

        self._sort = sort
        # use global settings for parameters that are not specified
        self._include = self._exclude = self._include_dir = self._exclude_dir = None
        for option in 'include', 'exclude', 'include_dir', 'exclude_dir':
           # this will set value to the value of the given keyword arg, or global setting if None, or "" if None
           value = settings.files.get("", **{option: locals()[option]})
           if type(value) is str:
               value = value.split()
           setattr(self, "_"+option, value)
        self._include_empty, self._show_hidden = settings.files.get(include_empty=include_empty, show_hidden=show_hidden)

        # init base FileList as empty initially, this will be populated by _load_impl()
        FileList.__init__(self, content=None, path=name, sort=sort)

        # subsets of content
        self._fits = self._others = self._images = self._dirs = self._tables = None

        # any list manipulations will cause a call to self._load()
        for method in 'append', 'extend', 'insert', 'pop', 'remove','reverse':
            list_method = getattr(FileList, method)
            def wrap_method(method, *args, **kw):
                self._load()
                method(self, *args, **kw)
            setattr(self, method, lambda method=method, *args, **kw: wrap_method(method=method, *args, **kw))

    def _scan_impl(self):
        # init our file list
        self[:] = []
        self.ndirs = self.nfiles = 0
        for filename in os.listdir(self.fullpath):
            # skip hidden files and directories, unless told not to
            if not self._show_hidden and filename[0] == ".":
                continue
            path = os.path.join(self.fullpath, filename)
            filetype = autodetect_file_type(path)
            # include/exclude based on patterns
            if os.path.isdir(path):
                if not _matches(filename, self._include_dir, self._exclude_dir):
                    continue
                # omit if empty
                if not self._include_empty and not object:
                    continue
                self.ndirs += 1
            else:
                if not _matches(filename, self._include, self._exclude):
                    continue
                self.nfiles += 1
            list.append(self, (filetype, path))
        # call base class scan
        FileList._scan_impl(self)

    def _load_impl(self):
        """Finally scan the directory and make a filelist object"""
        content = []
        for filetype, path in self:
            if filetype is DataDir:
                object = DataDir(path, include=self._include, exclude=self._exclude,
                                 include_dir=self._include_dir, exclude_dir=self._exclude_dir,
                                 include_empty=self._include_empty, show_hidden=self._show_hidden, sort=self._sort)
#                                 _skip_js_init=self._skip_js_init)
            else:
                object = filetype(path)
            content.append(object)
        self._set_list(content, self._sort)

    def _typed_subset(self, filetype, title):
        if not os.path.samefile(self.fullpath, radiopadre.ROOTDIR):
            title = "{}, {}".format(title, self.fullpath)
        return FileList([f for f in self if type(f) is filetype], path=self.fullpath, classobj=filetype, title=title, parent=self)

    @property
    def dirs(self):
        if self._dirs is None:
            self._dirs = self._typed_subset(DataDir, title="Subdirectories")
        return self._dirs

    @property
    def fits(self):
        if self._fits is None:
            # make separate lists of fits files and image files
            self._fits = self._typed_subset(FITSFile, title="FITS files")
        return self._fits

    @property
    def images(self):
        if self._images is None:
            self._images = self._typed_subset(ImageFile, title="Images")
        return self._images
    
    @property
    def tables(self):
        if self._tables is None:
            self._tables = self._typed_subset(CasaTable, title="Tables")
        return self._tables

    def __getitem__(self, *args, **kw):
        self._load()
        return FileList.__getitem__(self, *args, **kw)

    def __getslice__(self, *args, **kw):
        self._load()
        return FileList.__getslice__(self, *args, **kw)

    def __contains__(self, *args, **kw):
        self._load()
        return FileList.__contains__(self, *args, **kw)

    def __iter__(self, *args, **kw):
        self._load()
        return FileList.__iter__(self, *args, **kw)



