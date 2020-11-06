from sys import setprofile
from IPython.display import display, HTML, Javascript
import os
import fnmatch
import itertools
import uuid

from .file import FileBase
from .render import render_table, render_preamble, rich_string, render_titled_content, RichString

from . import executor

import radiopadre
from radiopadre import settings

class FileList(FileBase, list):
    @staticmethod
    def list_to_string(filelist, title=None):
        return "{}:\n{}".format(filelist._header_text(title=title), "\n".join(
                            ["{}: {}".format(i, d.path) for i, d in enumerate(filelist)]))

    class Title(object):
        """Class to manage FileList titles"""
        def __init__(self, provenance, *subset, is_path=True):
            """
            A title is formed as "provenance [subset, ....]
            """
            if type(provenance) is RichString:
                self.provenance = provenance
            else:
                tclass = 'rp-filelist-path' if is_path else 'rp-filelist-title'
                self.provenance = rich_string(provenance, div_class=tclass)
            self.subset = subset or []
            if subset:
                subset_str = rich_string("[" + ", ".join(self.subset) + "]", div_class='rp-filelist-subset')
                self.title = self.provenance + " " + subset_str
            else:
                self.title = self.provenance

        def __call__(self, *subsets):
            """
            title(subsets,...) returns a title with additional subsets
            """
            return FileList.Title(self.provenance, *(list(self.subset)+list(subsets)))

        def __add__(self, other):
            """
            Adding two titles of same provenance keeps provenance and adds subsets
            Otherwise, starts a new provenance (by adding the full titles together), and clears the subset.
            """
            if self.provenance == other.provenance:
                return FileList.Title(self.provenance, *(list(self.subset)+list(other.subset)))
            else:
                return FileList.Title(self.title + ", " + other.title)


    def __init__(self, content=None, path=".", extcol=False, showpath=False,
                 title=None,
                 parent=None, sort="xnt"):
        """

        """
        self._extcol = extcol
        self._showpath = showpath
        self._parent = parent
        self._sort = sort or ""
        self.nfiles = self.ndirs = 0
        self._fits = self._images = self._dirs = self._tables = self._html_files = None

        if type(title) is FileList.Title:
            self._list_title = title
        else:
            self._list_title = FileList.Title(provenance=title)

        FileBase.__init__(self, path or '.', title=self._list_title.title)

        if content is not None:
            self._set_list(content, sort)

        # # For every _show_xxx() method defined in the class object,
        # # create a corresponding self.xxx() method that maps to it
        # for method in dir(classobj):
        #     if method.startswith("_show_"):
        #         func = getattr(classobj, method)
        #         setattr(self, method[6:], lambda func=func,**kw:self._call_collective_method(func, **kw))

    def _set_list(self, content, sort=None):
        if sort:
            content = FileBase.sort_list(content, sort)
        self[:] = content
        self.nfiles = self.ndirs = 0
        # get summary
        for item in self:
            if os.path.isdir(item.fullpath):
                self.ndirs += 1
            else:
                self.nfiles += 1
        if len(set([os.path.dirname(item.fullpath) for item in self])) > 1:
            self._showpath = True
        self._reset_summary()

    def _reset_summary(self):
        desc = "{} file{}".format(self.nfiles, "s" if self.nfiles != 1 else "")
        if self.ndirs:
            desc += ", {} dir{}".format(self.ndirs, "s" if self.ndirs != 1 else "")
        self.description = desc
        self.size = desc

    def _get_collective_method(self, method):
        """If all contents belong to the same class, and that class has the given method defined, return it.
        Else return None."""
        # are we a single-class list?
        object_classes = set([type(x) for x in self])
        if len(object_classes) != 1:
            return None
        return getattr(object_classes.pop(), method, None)


    def render_html(self, ncol=None, context=None, title=None, subtitle=None, collapsed=None, **kw):
        self._load()
        title_html = self._header_html(title=title, subtitle=self.description if subtitle is None else subtitle)
        buttons_html = content_html = ""

        if collapsed is None and settings.gen.collapsible:
            collapsed = False

        arrow = "&uarr;" if "r" in self._sort else "&darr;"
        # find primary sort key ("d" and "r" excepted)
        sort = self._sort.replace("r", "").replace("d", "")
        primary_sort = sort and sort[0]
        tooltips = {}

        # get collective action buttons, if available
        action_buttons = self._get_collective_method('_collective_action_buttons_')
        if action_buttons:
            buttons_html = action_buttons(self, context=context)

        # if class object has a summary function, use that
        html_summary = self._get_collective_method('_html_summary')

        if html_summary:
            content_html = html_summary(self, context=context, primary_sort=primary_sort, sort_arrow=arrow)
        elif not self:
            collapsed = None
        else:
            # else fall back to normal filelist
            # auto-set 1 or 2 columns based on filename length
            if ncol is None:
                max_ = max([len(df.basename) for df in self])
                ncol = 2 if max_ <= settings.gen.twocolumn_list_width else 1

            def ext(df):
                return df.ext+"/" if os.path.isdir(df.path) else df.ext

            def link(df):
                return df.downloadable_url

            if self._extcol:
                labels = ("{}name".format(arrow if primary_sort == "n" else ""),
                        "{}ext".format(arrow  if primary_sort == "x" else ""),
                        "{}size".format(arrow if primary_sort == "s" else ""),
                        "{}modified".format(arrow if primary_sort == "t" else ""))
                data = [((df.basepath if self._showpath else df.basename), ext(df),
                        df.size, df.mtime_str)
                        for df in self]
                links = [(link(df), link(df), None, None) for df in self]
            else:
                labels = (arrow+"name" if primary_sort == "n" else
                            ("name {}ext".format(arrow) if primary_sort == "x" else "name"),
                        "{}size".format(arrow if primary_sort == "s" else ""),
                        "{}modified".format(arrow if primary_sort == "t" else ""))
                data = [((df.basepath if self._showpath else df.basename) + ext(df),
                        df.size, df.mtime_str) for df in self]
                links = [(link(df), None, None) for df in self]
            tooltips = { (irow,labels[0]): df.path for irow, df in enumerate(self) }
            # get "action buttons" associated with each file
            actions = [ df._action_buttons_(context) for df in self ]
            content_html = render_table(data, labels, links=links, ncol=ncol, actions=actions,
                                tooltips=tooltips,
                                context=context)
        return render_preamble() + \
                render_titled_content(title_html=title_html,
                                        buttons_html=buttons_html,
                                        content_html=content_html,
                                        collapsed=collapsed)

    def render_text(self, title=None, **kw):
        self._load()
        return FileList.list_to_string(self, title=title)

    @property
    def downloadable_url(self):
        return None

    def _scan_impl(self):
        FileBase._scan_impl(self)
        self._fits = self._images = self._dirs = self._tables = self._html_files = None
        self._reset_summary()

    # def watch(self,*args,**kw):
    #     display(HTML(render_refresh_button()))
    #     self.show_all(*args,**kw)

    def render_thumbnail_catalog(self, ncol=None, mincol=None, maxcol=None, context=None, title=None, titles=True, buttons=True, 
                                 collapsed=None, **kw):
        self._load()
        with self.transient_message("Rendering {} thumbnail(s)".format(len(self))):
            def _make_thumb(num_item):
                return num_item[1].thumb(prefix=num_item[0], title=None if titles else False, buttons=buttons, **kw)

            if executor.ncpu() < 2:
                thumbs = list(map(_make_thumb, enumerate(self)))
            else:
                thumbs = list(executor.executor().map(_make_thumb, enumerate(self)))

            if collapsed is None:
                collapsed = settings.thumb.collapsed
                if collapsed is None and settings.gen.collapsible:
                    collapsed = False

            title_html = self._header_html(title=title)
            buttons_html = content_html = ""
            
            action_buttons = self._get_collective_method('_collective_action_buttons_')
            if action_buttons:
                buttons_html = action_buttons(self, context=context)
   
            if thumbs:
                content_html = radiopadre.tabulate(thumbs, ncol=ncol, cw="equal",
                                    mincol=mincol or settings.thumb.mincol, maxcol=maxcol or settings.thumb.maxcol,
                                    zebra=False, align="center").render_html(context=context, **kw)
            else:
                collapsed = None                                    

            return render_preamble() + \
                   render_titled_content(title_html=title_html,
                                          buttons_html=buttons_html,
                                          content_html=content_html,
                                          collapsed=collapsed)


    @property
    def thumbs(self):
        return self._rendering_proxy('render_thumbnail_catalog', 'thumbs', arg0='ncol')

    def show_all(self, *args, **kw):
        # display(HTML(render_refresh_button(full=self._parent and self._parent.is_updated())))
        if not self:
            display(HTML("<DIV>0 files</DIV>"))
        for f in self:
            f.show(*args, **kw)

    def __call__(self, *patterns):
        """Returns a FileList of files from this list that match a pattern. Use !pattern to invert the meaning.
        Use -flags to apply a sort order (where flags is one or more of xntr, to sort by extension, name, time, and reverse)"""
        self.rescan()
        sort = None
        files = []
        subsets = []
        for patt in itertools.chain(*[x.split() for x in patterns]):
            if patt[0] == '!':
                files += [f for f in self if not fnmatch.fnmatch((f.path if self._showpath else f.name), patt[1:])]
                subsets.append(patt)
            elif patt[0] == '-':
                sort = patt[1:]
            else:
                files += [f for f in self if fnmatch.fnmatch((f.path if self._showpath else f.name), patt)]
                subsets.append(patt)
        if subsets:
            self.message(f"{','.join(subsets)}: {len(files)} match{'es' if len(files) !=1 else ''}")
        else:
            files = list(self)
        if sort is not None:
            subsets.append(f"sort: {sort}")

        return FileList(files,
                        path=self.fullpath, extcol=self._extcol, showpath=self._showpath, sort=sort or self._sort,
                        title=self._list_title(*subsets), parent=self._parent)

    def __getitem__(self, item):
        self._load()
        if type(item) is slice:
            slice_str = "{}:{}".format(item.start if item.start else '',
                                       item.stop if item.stop is not None and item.stop < 2**31 else "")
            if item.step:
                slice_str += ":{}".format(item.step)
            return FileList(list.__getitem__(self, item),
                            path=self.fullpath, extcol=self._extcol, showpath=self._showpath,
                            sort=self._sort, title=self._list_title(slice_str),
                            parent=self._parent)
        elif type(item) is str:
            newlist = self.__call__(item)
            if not newlist:
                self.message("{}: no match".format(item), color="red")
                return None
            else:
                if len(newlist) > 1:
                    self.message("{}: {} matches, returning the first".format(item, len(newlist)), color="red")
                else:
                    self.clear_message()
                return newlist[0]
        else:
            return list.__getitem__(self, item)

    def __getslice__(self, start, stop):
        return self.__getitem__(slice(start, stop))

    def __iadd__(self, other):
        return self + other

    def __add__(self, other):
        if not isinstance(other, FileList):
            raise TypeError("can't add object of type {} to {}".format(type(other), type(self)))
        self._load()
        other._load()
        content = list.__add__(self, other)
        showpath = self._showpath or other._showpath or self.fullpath != other.fullpath
        
        return FileList(content=content, path=self.path, sort=None, showpath=showpath, 
                        title=self._list_title+other._list_title, parent=self._parent)

    def filter(self, conditional, title=None):
        self._load()
        name = title or getattr(conditional, '__name__') or str(conditional)
        title = "{}, [filter: {}]".format(self._title, name)
        return FileList([f for f in self if conditional(f)],
                        path=self.fullpath, extcol=self._extcol, showpath=self._showpath,
                        sort=None, title=self._list_title(f"filter: {name}"), 
                        parent=self._parent)


    def sort(self, opt="dxnt"):
        self._load()
        return FileList(FileBase.sort_list(self, opt),
                        path=self.fullpath, extcol=self._extcol, showpath=self._showpath,
                        sort=opt, title=self._list_title(f"sort: {opt}"),
                        parent=self._parent)

    def _typed_subset(self, filetype, name):
        return FileList([f for f in self if type(f) is filetype], path=self.fullpath, 
                        title=self._list_title(name),
                        parent=self, sort=self._sort)

    @property
    def dirs(self):
        from .datadir import DataDir
        if self._dirs is None:
            self._dirs = self._typed_subset(DataDir, name="Subdirs")
        return self._dirs

    @property
    def fits(self):
        from .fitsfile import FITSFile
        if self._fits is None:
            # make separate lists of fits files and image files
            self._fits = self._typed_subset(FITSFile, name="FITS files")
        return self._fits

    @property
    def images(self):
        from .imagefile import ImageFile
        if self._images is None:
            self._images = self._typed_subset(ImageFile, name="Images")
        return self._images

    @property
    def tables(self):
        from .casatable import CasaTable
        if self._tables is None:
            self._tables = self._typed_subset(CasaTable, name="Tables")
        return self._tables

    @property
    def html(self):
        from .htmlfile import HTMLFile
        if self._html_files is None:
            self._html_files = self._typed_subset(HTMLFile, name="HTML files")
        return self._html_files


