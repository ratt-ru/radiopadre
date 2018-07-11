import IPython
from IPython.display import display, HTML, Javascript
import os
import fnmatch
import time

from .file import data_file, FileBase
from .filelist import FileList
from .fitsfile import FITSFile
from .imagefile import ImageFile
from .render import render_table, render_preamble, render_refresh_button, render_status_message, render_url, render_title

import radiopadre

class DataDir(FileBase):
    """
    This class represents a directory in the data folder
    """

    def __init__(self, name, files=None, root=".", original_root=None, _skip_js_init=False):
        FileBase.__init__(self, name, root=root)
        if not _skip_js_init:
            radiopadre._init_js_side()
        # list of files
        if files is None:
            files = os.listdir(self.fullpath)
        files = [f for f in files if not f.startswith('.')]
        # our title, in HTML
        self._original_root = root
        self._title = os.path.join(original_root or root, self.path) or '.'

        # make list of data filesD and sort by time
        self.files = FileList([data_file(os.path.join(self.fullpath, f),
                                         root=root) for f in files],
                              title=self._title, parent=self)

        # make separate lists of fits files and image files
        self.fits = FileList([f for f in self.files if type(f) is FITSFile],
                             classobj=FITSFile,
                             title="FITS files, " + self._title, parent=self)
        self.images = FileList([f for f in self.files if type(f) is ImageFile],
                               classobj=ImageFile,
                               title="Images, " + self._title, parent=self)
        self.others = FileList([f for f in self.files
                                if type(f) is not ImageFile and type(
                f) is not FITSFile],
                               title="Other files, " + self._title, parent=self)

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

    def __call__(self, pattern):
        return self.files(pattern)

    def __getslice__(self, *slc):
        return self.files.__getslice__(*slc)

    def __getitem__(self, item):
        return self.files[item]

    def ls(self):
        return DirList(self.path, recursive=False,
                       original_rootfolder=os.path.join(self._original_root, self.path))

    def lsr(self):
        return DirList(self.path, recursive=True,
                       original_rootfolder=os.path.join(self._original_root, self.path))

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
                           time.strftime(radiopadre.TIMEFORMAT, time.localtime(dir_.mtime))]
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
