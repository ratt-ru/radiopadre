import IPython
from IPython.display import display, HTML, Javascript
import os
import fnmatch
import subprocess
import itertools
import glob
import traceback
import inspect
from collections import OrderedDict

from .file import FileBase, autodetect_file_type
from .filelist import FileList
from .textfile import NumberedLineList
from .render import rich_string, TransientMessage

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
        patt_dir, patt_name = os.path.split(pattern)
        path_dir, path_name = os.path.split(path)
        return fnmatch.fnmatch(patt_dir, path_dir) and fnmatch.fnmatch(patt_name, path_name)
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
                 recursive=False, showpath=False, include_self=False,
                 title=None,
                 sort="dxnt"):
        """
        """

        self._sort = sort
        self._recursive = recursive
        self._browse_mode = include is None
        self._include_self = include_self

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

        # make title
        title = FileList.Title(name[2:] if name.startswith("./") else name, *(include or []))

        FileList.__init__(self, content=None, path=name, sort=sort, title=title, showpath=recursive or showpath)

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
                    if self._recursive:
                        if self._browse_mode:
                            if filetype is DataDir and _matches(name, self._include_dir, self._exclude_dir):
                                subdirs.append(name)
                        # Else descend unless directory excluded specifically
                        elif _matches(name, ["*"], self._exclude_dir):
                            subdirs.append(name)

            # Descend into specified subdirs
            dirs[:] = subdirs

        if self._include_self:
            list.append(self, (DataDir, self.fullpath))
        # call base class scan
        FileList._scan_impl(self)

    def _load_impl(self):
        """Finally scan the directory and make a filelist object"""
        content = []
        for filetype, path in self:
            if path is self:
                obj = self
            elif filetype is DataDir:
                obj = DataDir(path, include=self._default_include, exclude=self._default_exclude,
                                 include_dir=self._default_include_dir, exclude_dir=self._default_exclude_dir,
                                 include_empty=self._default_include_empty, show_hidden=self._default_show_hidden,
                                 sort=self._sort)
            else:
                obj = filetype(path)
            content.append(obj)
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
        except subprocess.CalledProcessError as exc:
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


def _ls_impl(recursive, sort, arguments, kw):
    """Creates a DataDir or FileList from the given arguments (name and/or patterns)

    - nothing (scan '.' with default patterns)
    - one directory, no patterns (scan directory with default patterns)
    - one or more patterns (use glob, make a FileList)

    """
    content = []
    messages = []
    showpath = False

    for arg in arguments:
        if os.path.isdir(arg):
            filetype = autodetect_file_type(arg)
            if arg[-1] == '/' or filetype is DataDir:
                dd = DataDir(arg, recursive=recursive, include_self=recursive, title=arg, sort=sort, showpath=True)
                if len(dd):
                    content.append(dd)
                    messages.append("{}: {} files".format(arg, len(dd)))
            else:
                content.append(FileList([filetype(arg)], title=arg, sort=None))
                messages.append("{}: {}".format(arg, filetype.__name__))
        else:
            files = []
            for path in glob.glob(arg):
                filetype = autodetect_file_type(path)
                if filetype is not None:
                    files.append(filetype(path))
            if files:
                content.append(FileList(files, sort=sort, title=arg))
                messages.append("{}: {} matches".format(arg, len(files)))
            else:
                messages.append("{}: no matches".format(arg))

    global _transient_message
    _transient_message = TransientMessage("; ".join(messages), color="blue" if content else "red")

    # display section title
    if 'section' in kw:
        from radiopadre.layouts import Section
        Section(kw['section'])

    if len(content) == 1:
        return content[0]
    else:
        return FileList(itertools.chain(*content), path=".", title=", ".join(arguments), sort=sort)


def _ls(recursive, default_sort, unsplit_arguments, kw):
    # split all arguments on whitespace and form one big list
    local_vars = inspect.currentframe().f_back.f_back.f_locals
    
    arguments = list(itertools.chain(*[arg.format(**local_vars).split() for arg in unsplit_arguments]))

    # check for sort order and recursivity
    sort = ""
    paths = []
    for arg in arguments:
        # arguments starting with "-" are sort keys. 'R' forces recursive mode
        if arg[0] == '-':
            for char in arg[1:]:
                if char == 'R':
                    recursive = True
                else:
                    sort += char
        else:
            paths.append(arg)
    
    return _ls_impl(sort=sort or default_sort, recursive=recursive, arguments=paths or ["."], kw=kw)



def ls(*args, **kw):
    """
    Creates a DataDir from '.' non-recursively, optionally applying a file selection pattern.
    Sorts in default order (directory, extension, name, mtime)
    """
    return _ls(False, '-dxnt', args, kw)

def lst(*args, **kw):
    """
    Creates a DataDir from '.' non-recursively, optionally applying a file selection pattern.
    Sorts in time order (directory, mtime, extension, name)
    """
    return _ls(False, '-dtxn', args, kw)

def lsrt(*args, **kw):
    """
    Creates a DataDir from '.' non-recursively, optionally applying a file selection pattern.
    Sorts in reverse time order (directory, -mtime, extension, name)
    """
    return _ls(False, '-rtdxn', args, kw)

def lsR(*args, **kw):
    """
    Creates a DataDir from '.' recursively, optionally applying a file selection pattern.
    Sorts in default order (directory, extension, name, mtime)
    """
    return _ls(True, '-dxnt', args, kw)


