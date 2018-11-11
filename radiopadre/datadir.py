import IPython
from IPython.display import display, HTML, Javascript
import os
import fnmatch
import time

from .file import FileBase, autodetect_file_type
from .filelist import FileList
from .fitsfile import FITSFile
from .imagefile import ImageFile
from .render import render_table, render_preamble, render_refresh_button, render_status_message, render_url, render_title

import radiopadre
from radiopadre import settings

# Need a flag raised in show() and other methods which prevents _load_impl() from being invoked.
# Decorators wrappig methods, and with?
#

def _matches(filename, include_patterns=(), exclude_patterns=()):
    """
    Returns True if filename matches a set of include/exclude patterns.
    If include is set, filename MUST be in an include pattern. Filename cannot be in any exclude pattern.
    """
    if include_patterns and not any([fnmatch.fnmatch(filename, patt) for patt in include_patterns]):
        return False
    return not any([fnmatch.fnmatch(filename, patt) for patt in exclude_patterns])

class DataDir(FileBase, FileList):
    """
    This class represents a directory
    """

    def __init__(self, name, root=".",
                 include=None, exclude=None,
                 include_dir=None, exclude_dir=None,
                 include_empty=None, show_hidden=None,
                 sort="dxnt",
                 _skip_js_init=False):
        """
        """

        # make sure Javascript end is initialized
        self._skip_js_init = _skip_js_init
        if not _skip_js_init:
            radiopadre._init_js_side()

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

        # init base class -- this will call _scan_impl
        FileBase.__init__(self, name, root=root)
        # our title, in HTML
        FileList.__init__(self, None, sort=sort, title=os.path.join(root, self.path))

        # subsets of content
        self._fits = self._others = self._images = self._dirs = None

        # any list manipulations will cause a call to self._load()
        for method in 'append', 'extend', 'insert', 'pop', 'remove','reverse':
            list_method = getattr(FileList, method)
            def wrap_method(*args, **kw):
                self._load()
                list_method(self, *args, **kw)
            setattr(self, method, wrap_method)

    def _scan_impl(self):
        FileBase._scan_impl(self)
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
            if filetype is DataDir:
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
            self.append((filetype, path))

        self.description = "{} files".format(self.nfiles)
        if self.ndirs:
            self.description += ", {} dirs".format(self.ndirs)

    def _load_impl(self):
        """Finally scan the directory and make a filelist object"""
        print "loading",self.fullpath
        content = []
        for filetype, path in self:
            if filetype is DataDir:
                object = DataDir(path, root=self._root, include=self._include, exclude=self._exclude,
                                 include_dir=self._include_dir, exclude_dir=self._exclude_dir,
                                 include_empty=self._include_empty, show_hidden=self._show_hidden, sort=self._sort,
                                 _skip_js_init=self._skip_js_init)
            else:
                object = filetype(path, self._root)
            content.append(object)
        self._set_list(content, self._sort)

    def _typed_subset(self, filetype, title):
        return FileList([f for f in self if type(f) is filetype], classobj=filetype, title=title, parent=self)

    @property
    def dirs(self):
        if self._dirs is None:
            self._dirs = self._typed_subset(DataDir, "Subdirectories, " + self._title)
        return self._dirs

    @property
    def fits(self):
        if self._fits is None:
            # make separate lists of fits files and image files
            self._fits = self._typed_subset(FITSFile, "FITS files, " + self._title)
        return self._fits

    @property
    def images(self):
        if self._images is None:
            self._images = self._typed_subset(ImageFile, title="Images, " + self._title)
        return self._images


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



class DirList(list):
    def __init__(self, rootfolder=None, include="*.jpg *.png *.fits *.txt *.log",
                 exclude=".* .*/", exclude_empty=True, original_rootfolder=None,
                 sort="xnt",
                 recursive=True, title=None, _scan=True):
        """
        Creates a DirList object corresponding to a rootfolder and (optionally)
        all its subdirectories.

        Args:
            recursive: set to False to make non-recursive list
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
            title:  the title of the directory list -- uses
                original_rootfolder or rootfolder by default
            sort:   sort order, default is 'xnt'
            _scan: (for internal use only) if False, directory is not re-scanned
        """
        radiopadre._init_js_side()
        self._root = rootfolder = rootfolder or os.environ.get('PADRE_DATA_DIR') or '.'
        self._original_root = original_rootfolder or os.environ.get('PADRE_HOST_DATA_DIR') or rootfolder
        self._title = title or self._original_root

        # setup exclude/include patterns
        include_files = include.split()
        exclude_files = [f for f in exclude.split() if f[-1] != '/']
        exclude_dirs = [f[:-1] for f in exclude.split() if f[-1] == '/'] + [
            "radiopadre-thumbnails"]
        #
        if _scan:
            if not os.path.exists(rootfolder):
                raise IOError("directory %s does not exist" % rootfolder)
            for dir_, dirnames, files in os.walk(rootfolder):
                # exclude subdirectories
                if not recursive and dir_ != rootfolder:
                    dirnames[:] = []
                else:
                    dirnames[:] = [d for d in dirnames
                                   if not any([fnmatch.fnmatch(d, patt) for patt in exclude_dirs])]
                # get files matching include/exclude filters, and weed out
                # non-existent ones (i.e. dangling symlinks)
                files = [f for f in files
                         if any(
                        [fnmatch.fnmatch(f, patt) for patt in include_files])
                         and not any(
                        [fnmatch.fnmatch(f, patt) for patt in exclude_files])
                         and os.path.exists(os.path.join(dir_, f))
                         ]
                if files or not exclude_empty:
                    self.append(DataDir(dir_, files, root=rootfolder,
                                        original_root=original_rootfolder, _skip_js_init=True))
        # init lists
        self.sort(sort)

    def latest(self, num=1):
        if not self:
            raise IOError("no subdirectories in %s" % self._root)
        return self.sort("t")[-num]

    def sort(self, opt="xnt"):
        self._sort_option = opt
        FileBase.sort_list(self, opt)
        # set up aggregated file lists
        self.files = FileList(title=self._title, showpath=True, parent=self)
        self.fits = FileList(classobj=FITSFile,
                             title="FITS files, " + self._title, showpath=True, parent=self)
        self.images = FileList(classobj=ImageFile,
                               title="Images, " + self._title, showpath=True, parent=self)
        self.others = FileList(title="Other files, " + self._title,
                               showpath=True, parent=self)
        for d in self:
            for attr in 'files', 'fits', 'images', 'others':
                getattr(self, attr).extend(getattr(d, attr))
        return self

    def is_updated(self):
        return any([d.is_updated() for d in self])

    def _repr_html_(self, copy_filename=None, copy_dirs='dirs', copy_root='root', **kw):
        """Render DirList in HTML. If copy is not None, adds buttons to make copies
        of the notebook under subdir/COPY.ipynb"""
        html = render_preamble() + render_title(self._title) + \
               render_refresh_button(full=self.is_updated())
        if not self:
            return html + ": no subdirectories"
        dirlist = []
        for dir_ in self:
            nfits = len(dir_.fits)
            nimg = len(dir_.images)
            nother = len(dir_.files) - nfits - nimg
            table_entry = [dir_.path or '.', nfits, nimg, nother,
                           time.strftime(settings.gen.timeformat, time.localtime(dir_.mtime))]
            if copy_filename:
                # if copy of this notebook exists in subdirectory, show "load copy" button
                copypath = os.path.join(dir_.fullpath, copy_filename + ".ipynb")
                if os.path.exists(copypath):
                    button = """<A href=%s target='_blank'
                                title="%s contains its own copy of this notebook, click to open."
                                >open custom copy of notebook</a>""" % (
                        render_url(copypath, "notebooks"),
                        dir_.name)
                # else show "make copy" button
                else:
                    #                    button = """<button onclick="console.log('%s');"
                    button = """<a href='#' onclick="document.radiopadre.copy_notebook('%s','%s','%s'); return false;" 
                                title="Click to make a new copy of this radiopadre notebook in %s."
                                >create custom copy of notebook</a>""" % (copypath, copy_dirs, copy_root, dir_.name)
                table_entry.append(button)
            dirlist.append(table_entry)
        labels = ["name", "# FITS", "# img", "# others", "modified"]
        copy_filename and labels.append("copy")
        html += render_table(dirlist, labels=labels, html=["copy"])
        return html

    def __str__(self):
        return FileList.list_to_string(self)

    def show(self, **kw):
        return display(HTML(self._repr_html_(**kw)))

    def list(self, **kw):
        return display(HTML(self._repr_html_(**kw)))

    def subdirectory_catalog(self, basename="results", dirs="dirs", root="root", **kw):
        return display(HTML(self._repr_html_(copy_filename=basename, copy_dirs=dirs, copy_root=root, **kw)))

    def __call__(self, pattern):
        newlist = DirList(self._root, _scan=False, title="%s/%s" % (self._title,
                                                                    pattern))
        for patt in pattern.split():
            newlist += [d for d in self if fnmatch.fnmatch(d.path, patt)]
        newlist.sort(self._sort_option)
        return newlist

    def __getslice__(self, *slc):
        newlist = DirList(self._root, _scan=False,
                          title="%s[%s]" % (
                              self._title, ":".join(map(str, slc))))
        newlist += list.__getslice__(self, *slc)
        newlist.sort(self._sort_option)
        return newlist
