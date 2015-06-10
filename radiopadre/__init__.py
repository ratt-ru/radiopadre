import time
import fnmatch
import os

import astropy

import IPython.display
import IPython.display
from IPython.display import HTML, display, display_javascript, display_html
from radiopadre.fitsfile import FITSFile
from radiopadre.imagefile import ImageFile
from radiopadre.file import data_file, FileBase
from radiopadre.render import *

import radiopadre.notebook_utils
from radiopadre.notebook_utils import _notebook_save_hook

__version__ = '0.3'

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

## various notebook-related init
astropy.log.setLevel('ERROR')

def _init_js_side ():
    """Checks that Javascript components of radiopadre are initialized"""
    try:
        get_ipython
    except:
        return None
    get_ipython().magic("matplotlib inline")
    # load radiopadre/js/init.js and init controls
    initjs = os.path.join(os.path.dirname(__file__),"js","init.js")
    display(Javascript(open(initjs).read()))
    display(Javascript("document.radiopadre.init_controls('%s')"%os.environ['USER']))

def protect (author=None):
    """Makes current notebook protected with the given author name. Protected notebooks won't be saved
    unless the user matches the author."""
    author = author or os.environ['USER']
    display(Javascript("document.radiopadre.protect('%s')"%author))
    display(HTML(render_status_message("""This notebook is now protected, author is "%s".
        All other users will have to treat this notebook as read-only.""" % author)))

def unprotect ():
    """Makes current notebook unprotected."""
    display(Javascript("document.radiopadre.unprotect()"))
    display(HTML(render_status_message("""This notebook is now unprotected.
        All users can treat it as read-write.""")))

class FileList(list):
    @staticmethod
    def list_to_string (filelist):
        return "Contents of %s:\n"%filelist._title + "\n".join(
                    ["%d: %s" % (i, d.path) or '.' for i, d in enumerate(filelist)])

    def __init__(self, files=[], extcol=True, showpath=False,
                 classobj=None, title="", parent=None,
                 sort="xnt"):
        list.__init__(self, files)
        self._extcol = extcol
        self._showpath = showpath
        self._classobj = classobj
        self._title = title
        self._parent = parent
        if sort:
            self.sort(sort)

    def sort(self, opt="xnt"):
        return FileBase.sort_list(self, opt)

    def _repr_html_(self, ncol=None, **kw):
        html = render_preamble() + render_title(self._title) + \
                render_refresh_button(full=self._parent and self._parent.is_updated());
        if not self:
            return html + ": 0 files"
        # auto-set 1 or 2 columns based on filename length
        if ncol is None:
            max_ = max([len(df.basename) for df in self])
            ncol = 2 if max_ <= TWOCOLUMN_LIST_WIDTH else 1
        if self._extcol:
            labels = "name", "ext", "size", "modified"
            data = [((df.basepath if self._showpath else df.basename), df.ext,
                     df.size_str, df.mtime_str) for df in
                    self]
            links = [(render_url(df.fullpath), render_url(df.fullpath), None, None) for df in self]
        else:
            labels = "name", "size", "modified"
            data = [((df.basepath if self._showpath else df.basename),
                     df.size_str, df.mtime_str) for df in self]
            links = [(render_url(df.fullpath), None, None) for df in self]
        html += render_table(data, labels, links=links, ncol=ncol)
        return html

    def show(self, ncol=None, **kw):
        return IPython.display.display(HTML(self._repr_html_(ncol=ncol, **kw)))

    def list(self, ncol=None, **kw):
        return IPython.display.display(HTML(self._repr_html_(ncol=ncol, **kw)))

    def __str__ (self):
        return FileList.list_to_string(self)

    def summary(self, **kw):
        kw.setdefault('title', self._title)
        kw.setdefault('showpath', self._showpath)
        summary = getattr(self._classobj, "_show_summary", None)
        if summary:
            display(HTML(render_refresh_button(full=self._parent and self._parent.is_updated())))
            return summary(self, **kw)  
        else:
            return self.list(**kw)

    # def watch(self,*args,**kw):
    #     display(HTML(render_refresh_button()))
    #     self.show_all(*args,**kw)

    def show_all(self,*args,**kw):
        display(HTML(render_refresh_button(full=self._parent and self._parent.is_updated())))
        if not self:
            display(HTML("<p>0 files</p>"))
        for f in self:
            f.show(*args,**kw)

    def __call__(self, pattern):
        files = []
        for patt in pattern.split():
            files += [f for f in self if
                      fnmatch.fnmatch((f.path if self._showpath else f.name),
                                      patt)]
        return FileList(files,
                        extcol=self._extcol, showpath=self._showpath,
                        classobj=self._classobj,
                        title=os.path.join(self._title, pattern), parent=self._parent)

    def thumbs(self, **kw):
        display(HTML(render_refresh_button(full=self._parent and self._parent.is_updated())))
        if not self:
            display(HTML("<p>0 files</p>"))
            return None
        kw.setdefault('title', self._title + " (%d file%s)" % (len(self), "s" if len(self) > 1 else ""))
        kw.setdefault('showpath', self._showpath)
        thumbs = getattr(self._classobj, "_show_thumbs", None)
        if thumbs:
            return thumbs(self, **kw) 
        display(HTML("<p>%d files. Don't know how to make thumbnails for this collection.</p>" % len(self)))

    def __getslice__(self, *slc):
        return FileList(list.__getslice__(self, *slc),
                        extcol=self._extcol, showpath=self._showpath,
                        classobj=self._classobj,
                        title="%s[%s]" % (self._title, ":".join(map(str, slc))), parent=self._parent)


class DataDir(FileBase):
    """
    This class represents a directory in the data folder
    """

    def __init__(self, name, files=None, root=".", original_root=None, _skip_js_init=False):
        FileBase.__init__(self, name, root=root)
        if not _skip_js_init:
            _init_js_side()
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

    def ls (self):
        return DirList(self.path, recursive=False, 
                original_rootfolder=os.path.join(self._original_root, self.path))

    def lsr (self):
        return DirList(self.path, recursive=True,  
                original_rootfolder=os.path.join(self._original_root, self.path))




def lsd (pattern=None,*args,**kw):
    """Creates a DirList from '.' non-recursively, optionally applying a pattern.

    Args:
        pattern: if specified, a wildcard pattern
    """
    kw['recursive'] = False
    dl = DirList(*args,**kw)
    return dl(pattern) if pattern else dl

def lsdr (pattern=None,*args,**kw):
    """Creates a DirList from '.' recursively, optionally applying a pattern.

    Args:
        pattern: if specified, a wildcard pattern
    """
    kw['recursive'] = True
    dl = DirList(*args,**kw)
    return dl(pattern) if pattern else dl

def latest (*args):
    """Creates a DirList from '.' recursively, optionally applying a pattern.

    Args:
        pattern (str):  if specified, a wildcard pattern
        num (int):      use 2 for second-latest, 3 for third-latest, etc.
    """
    args = dict([(type(arg),arg) for arg in args])
    dl = lsd(pattern=args.get(str),sort='txn')
    if not dl:
        raise IOError("no subdirectories here")
    return dl[-args.get(int, -1)].lsr()


class DirList(list):

    def __init__(self, rootfolder=None, include="*.jpg *.png *.fits *.txt",
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
        _init_js_side()
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
                    dirnames[:] = [ d for d in dirnames 
                                    if not any([fnmatch.fnmatch(d, patt) for patt in exclude_dirs]) ]
                # get files matching include/exclude filters
                files = [f for f in files
                         if any(
                             [fnmatch.fnmatch(f, patt) for patt in include_files])
                         and not any(
                             [fnmatch.fnmatch(f, patt) for patt in exclude_files])]
                if files or not exclude_empty:
                    self.append(DataDir(dir_, files, root=rootfolder,
                                        original_root=original_rootfolder, _skip_js_init=True))
        # init lists
        self.sort(sort)

    def latest (self, num=1):
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

    def is_updated (self):
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
            table_entry = [ dir_.path or '.', nfits, nimg, nother,
                            time.strftime(TIMEFORMAT, time.localtime(dir_.mtime)) ]
            if copy_filename:
                # if copy of this notebook exists in subdirectory, show "load copy" button
                copypath = os.path.join(dir_.fullpath,copy_filename+".ipynb")
                if os.path.exists(copypath):
                    button = """<A href=%s target='_blank'
                                title="%s contains its own copy of this notebook, click to open."
                                >open custom copy of notebook</a>""" % (
                                    render_url(copypath,"notebooks"),
                                    dir_.name)
                # else show "make copy" button
                else:
#                    button = """<button onclick="console.log('%s');" 
                    button = """<a href='#' onclick="document.radiopadre.copy_notebook('%s','%s','%s'); return false;" 
                                title="Click to make a new copy of this radiopadre notebook in %s."
                                >create custom copy of notebook</a>""" % (copypath, copy_dirs, copy_root, dir_.name)
                table_entry.append(button)
            dirlist.append(table_entry)
        labels = [ "name", "# FITS", "# img", "# others", "modified" ]
        copy_filename and labels.append("copy")
        html += render_table(dirlist, labels=labels, html=["copy"])
        return html

    def __str__ (self):
        return FileList.list_to_string(self)

    def show(self, **kw):
        return display(HTML(self._repr_html_(**kw)))

    def list(self, **kw):
        return display(HTML(self._repr_html_(**kw)))

    def subdirectory_catalog (self, basename="results", dirs="dirs", root="root", **kw):
        return display(HTML(self._repr_html_(copy_filename=basename,copy_dirs=dirs,copy_root=root,**kw)))

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

import IPython.nbformat
import json
from radiopadre.notebook_utils import scrub_cell

def copy_current_notebook(oldpath,newpath,cell=0,copy_dirs='dirs',copy_root='root'):
    # read notebook data
    data = open(oldpath).read()
    version = json.loads(data)['nbformat']
    nbdata = IPython.nbformat.reads(data,version)
    nbdata.keys()    
    # convert to current format
    current_version = IPython.nbformat.current_nbformat
    nbdata = IPython.nbformat.convert(nbdata, current_version)
    current_format = getattr(IPython.nbformat,'v'+str(current_version))
    # accommodate worksheets, if available 
    if hasattr(nbdata, 'worksheets'):
        raise RuntimeError,"copy_current_notebook: not compatible with worksheets"
    metadata = nbdata['metadata']
    cells = nbdata['cells']
    # strip out all cells up to and including indicated one
    del cells[:cell+1]
    # scrub cell output
    for c in cells:
        scrub_cell(c)
    # insert boilerplate code
    code = "import radiopadre\n" + \
           "%s = radiopadre.DirList('.')" % copy_dirs
    if copy_root:
        code += "\n%s = %s[0]" % (copy_root, copy_dirs)
    code += "\n%s.show()" % copy_dirs
    # insert output
    output = current_format.new_output("display_data",data={
      "text/html": [ "<b style='color: red'>Please select Cell|Run all from the menu to render this notebook.</b>" ]
      })
    cells.insert(0,current_format.new_code_cell(code,outputs=[output]))
    # insert markdown
    cells.insert(0, current_format.new_markdown_cell("""# %s\nThis
                radiopadre notebook was automatically generated from ``%s`` 
                using the 'copy notebook' feature. Please select "Cell|Run all"
                from the menu to render this notebook.
                """ % (newpath,oldpath),
    ))
    # cleanup metadata
    metadata['radiopadre_notebook_protect'] = 0
    metadata['radiopadre_notebook_scrub'] = 0
    if 'signature' in metadata:
        metadata['signature'] = ""
    # save
    IPython.nbformat.write(nbdata, open(newpath,'w'), version)
    return newpath
