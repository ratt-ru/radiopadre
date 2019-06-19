import IPython
from IPython.display import display, HTML, Javascript
import os
import fnmatch
import subprocess

from .file import FileBase, autodetect_file_type
from .filelist import FileList
from .textfile import NumberedLineList
from .render import render_table, render_preamble, render_refresh_button, rich_string, render_url, render_title

import radiopadre
from radiopadre import settings

# Need a flag raised in show() and other methods which prevents _load_impl() from being invoked.

def _match_pattern(path, pattern):
    """Matches path to pattern. If pattern contains a directory, matches full path, else only the basename"""
    if path.startswith("./"):
        path = path[2:]
    if pattern.startswith("./"):
        pattern = pattern[2:]
    if '/' in pattern:
        return fnmatch.fnmatch(path, pattern)
    else:
        return fnmatch.fnmatch(os.path.basename(path), pattern)

def _matches(filename, include_patterns=(), exclude_patterns=()):
    """
    Returns True if filename matches a set of include/exclude patterns.
    If include is set, filename MUST be in an include pattern. Filename cannot be in any exclude pattern.
    """
    if include_patterns and not any([_match_pattern(filename, patt) for patt in include_patterns]):
        return False
    return not any([_match_pattern(filename, patt) for patt in exclude_patterns])

class DataDir(FileList):
    """
    This class represents a directory
    """

    def __init__(self, name,
                 include=None, exclude=None,
                 include_dir=None, exclude_dir=None,
                 include_empty=None, show_hidden=None,
                 recursive=False,
                 title=None,
                 sort="dxnt"):
        """
        """

        self._sort = sort
        self._recursive = recursive
        self._browse_mode = include is None

        # use global settings for some parameters that are not specified
        self._default_include_empty, self._default_show_hidden = include_empty, show_hidden
        self._default_include, self._default_exclude = include, exclude
        self._default_include_dir, self._default_exclude_dir = include_dir, exclude_dir
        # the line below only serves to keep pycharm happy (otherwise it thinks the attributes are not initialized)
        self._include = self._exclude = self._include_dir = self._exclude_dir = None

        self._include_empty, self._show_hidden = settings.files.get(include_empty=include_empty, show_hidden=show_hidden)
        for option in 'include', 'exclude', 'include_dir', 'exclude_dir':
            # store keyword args to be passed to subdirs
            argvalue = getattr(self,"_default_"+option)
            # this will set value to the value of the given keyword arg, or global setting if None, or default if None
            default = "*" if option[:3] == "inc" else None
            value = settings.files.get(default, **{option: argvalue})
            if value is None:
                value = []
            else:
                if type(value) is str:
                    value = value.split(", ")
                value = list(value)
            setattr(self, "_"+option, value)
        # if not showing hidden, add ".*" to exclude patterns
        if not self._show_hidden:
            self._exclude.append(".*")
            self._exclude_dir.append(".*")

        FileList.__init__(self, content=None, path=name, sort=sort, title=title, showpath=recursive)

        if include:
            self.title += "/{}".format(','.join(include))
            self._reset_summary()

        # any list manipulations will cause a call to self._load()
        for method in 'append', 'extend', 'insert', 'pop', 'remove','reverse':
            list_method = getattr(FileList, method)
            def wrap_method(method, *args, **kw):
                self._load()
                method(self, *args, **kw)
            setattr(self, method, lambda method=method, *args, **kw: wrap_method(method=method, *args, **kw))

    def _scan_impl(self):
        # subsets of content
        self._fits = self._others = self._images = self._dirs = self._tables = None

        # init our file list
        self[:] = []
        self.ndirs = self.nfiles = 0

        # We have two modes of scanning:
        # Default "browse" mode (corresponding to an ls with no patterns), where we include
        #   * all files whose basename matches include/exclude patterns
        #   * all directories whose basename matches the include_dir+include/exclude_dir+exclude patterns, omitting
        #       empty ones (unless self._include_empty is set)
        #   * (in recursive mode) descend into directories matching include_dir/exclude_dir, which aren't a specific
        #       class such as CASA table
        #
        # Targeted "list" mode (corresponding to an ls with patterns), where we include:
        #   * all files whose path matches include/exclude patterns
        #   * all directories whose path matches the include/exclude patterns
        #   * (in recursive mode) descend into directories matching include_dir/exclude_dir, which aren't a specific
        #       class such as CASA table

        # Check for matching directories
        if self._browse_mode:
            incdir = self._include + self._include_dir
            excdir = self._exclude + self._exclude_dir
        else:
            incdir, excdir = self._include, self._exclude

        for root, dirs, files in os.walk(self.fullpath, followlinks=True):
            subdirs = []
            # Check for matching files
            for name in files:
                path = os.path.join(root, name)
                # check for symlinks to dirs
                if os.path.isdir(path):
                    dirs.append(name)
                # else handle as file
                else:
                    filetype = autodetect_file_type(path)
                    if filetype is not None and _matches(name if self._browse_mode else path, self._include, self._exclude):
                        list.append(self, (filetype, path))
                        self.nfiles += 1
            # Check for matching directories
            for name in dirs:
                path = os.path.join(root, name)
                filetype = autodetect_file_type(path)
                if filetype is not None:
                    if _matches(name if self._browse_mode else path, incdir, excdir) and \
                                (not self._browse_mode or self._include_empty or os.listdir(path)):
                        list.append(self, (filetype, path))
                        self.ndirs += 1
                    # Check for directories to descend into.
                    # In browse mode (no patterns), only descend into DataDir.
                    if self._browse_mode:
                        if self._recursive and filetype is DataDir and _matches(name, self._include_dir, self._exclude_dir):
                            subdirs.append(name)
                    # Else always descend (we'll match the path against a pattern)
                    else:
                        subdirs.append(name)

            # Descend into specified subdirs
            dirs[:] = subdirs

        # call base class scan
        FileList._scan_impl(self)

    def _load_impl(self):
        """Finally scan the directory and make a filelist object"""
        content = []
        for filetype, path in self:
            if filetype is DataDir:
                object = DataDir(path, include=self._default_include, exclude=self._default_exclude,
                                 include_dir=self._default_include_dir, exclude_dir=self._default_exclude_dir,
                                 include_empty=self._default_include_empty, show_hidden=self._default_show_hidden,
                                 sort=self._sort)
#                                 _skip_js_init=self._skip_js_init)
            else:
                object = filetype(path)
            content.append(object)
        self._set_list(content, self._sort)

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

    def sh(self, command, exception=False):
        cmd = "cd {}; {}".format(self.fullpath, command)
        try:
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
            retcode = 0
        except subprocess.CalledProcessError,exc:
            if exception:
                raise
            retcode = exc.returncode
            output = exc.output
        title = rich_string( "[{}$ {}]{}".format(self.path, command, " (return code {})".format(retcode) if retcode else ""),
                             "[{}$ <B>{}</B>]{}".format(self.path, command,
                                               " <SPAN style='color: red;'>(return code {})</SPAN>".format(retcode) if retcode else ""))
        return NumberedLineList(output.rstrip(), title=title)

    def shx(self, command):
        return self.sh(command, exception=True)


