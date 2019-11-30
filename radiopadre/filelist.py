import IPython
from IPython.display import display, HTML, Javascript
import os
import fnmatch
from collections import OrderedDict
import uuid
import itertools


from .file import FileBase
from .render import render_table, render_preamble, render_refresh_button, render_url, rich_string

import radiopadre
from radiopadre import settings

class FileList(FileBase, list):
    @staticmethod
    def list_to_string(filelist):
        return "{}:\n{}".format(filelist._header_text(), "\n".join(
                            ["{}: {}".format(i, d.path) for i, d in enumerate(filelist)]))

    def __init__(self, content=None, path=".", extcol=False, showpath=False,
                 title=None, parent=None,
                 sort="xnt"):
        self._extcol = extcol
        self._showpath = showpath
        self._parent = parent
        self._sort = sort or ""
        self.nfiles = self.ndirs = 0
        self._fits = self._images = self._dirs = self._tables = self._html_files = None

        FileBase.__init__(self, path or '.', title=title)

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


    def render_html(self, ncol=None, context=None, **kw):
        self._load()
        html = render_preamble() + self._header_html()
               # + render_refresh_button(full=self._parent and self._parent.is_updated())

        arrow = "&uarr;" if "r" in self._sort else "&darr;"
        # find primary sort key ("d" and "r" excepted)
        sort = self._sort.replace("r", "").replace("d", "")
        primary_sort = sort and sort[0]
        tooltips = {}

        # if class object has a summary function, use that
        html_summary = self._get_collective_method('_html_summary')

        if html_summary:
            return html + html_summary(self, context=context, primary_sort=primary_sort, sort_arrow=arrow)
        if not self:
            return html

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
        html += render_table(data, labels, links=links, ncol=ncol, actions=actions,
                             tooltips=tooltips,
                             context=context)
        return html

    def render_text(self):
        self._load()
        return FileList.list_to_string(self)

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

    def render_thumbnail_catalog(self, ncol=None, mincol=None, maxcol=None, context=None, **kw):
        self._load()
        thumbs = []
        with self.transient_message("Rendering {} thumbnail(s)".format(len(self))):
            for num, item in enumerate(self):
            # with self.transient_message("Rendering thumbnail {}/{}...".format(num, len(self))):
                thumbs.append(item.thumb(prefix=num, **kw))

            html = render_preamble() + self._header_html()

            action_buttons = self._get_collective_method('_collective_action_buttons_')
            if action_buttons:
                html += action_buttons(self, context=context)

            html += radiopadre.tabulate(thumbs, ncol=ncol,
                                mincol=mincol or settings.thumb.mincol, maxcol=maxcol or settings.thumb.maxcol,
                                zebra=False, align="center").render_html(context=context, **kw)
        return html

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
        """Returns a FileList os files from this list that match a pattern. Use !pattern to invert the meaning.
        Use -flags to apply a sort order (where flags is one or more of xntr, to sort by extension, name, time, and reverse)"""
        self.rescan()
        sort = None
        files = []
        accepted_patterns = []
        for patt in itertools.chain(*[x.split() for x in patterns]):
            if patt[0] == '!':
                files += [f for f in self if not fnmatch.fnmatch((f.path if self._showpath else f.name), patt[1:])]
                accepted_patterns.append(patt)
            elif patt[0] == '-':
                sort = patt[1:]
            else:
                files += [f for f in self if fnmatch.fnmatch((f.path if self._showpath else f.name), patt)]
                accepted_patterns.append(patt)
        title = self.title.copy()
        if accepted_patterns:
            if os.path.samefile(self.fullpath, radiopadre.ROOTDIR):
                title = ",".join(accepted_patterns)
            else:
                title += "/{}".format(",".join(accepted_patterns))
            self.message(title + ": {} match{}".format(len(files), "es" if len(files) !=1 else ""))
        if sort is not None:
            title += " [sort: {}]".format(sort)

        return FileList(files if accepted_patterns else list(self),
                        path=self.fullpath, extcol=self._extcol, showpath=self._showpath, sort=sort or self._sort,
                        title=title, parent=self._parent)

    # def thumbs(self, max=100, **kw):
    #     display(HTML(render_refresh_button(full=self._parent and self._parent.is_updated())))
    #     if not self:
    #         display(HTML("<p>0 files</p>"))
    #         return None
    #     kw.setdefault('title', self._title + " (%d file%s)" % (len(self), "s" if len(self) > 1 else ""))
    #     kw.setdefault('showpath', self._showpath)
    #     thumbs = getattr(self._classobj, "_show_thumbs", None)
    #     if thumbs:
    #         return thumbs(self[:max], **kw)
    #     display(HTML("<p>%d files. Don't know how to make thumbnails for this collection.</p>" % len(self)))

    def __getitem__(self, item):
        self._load()
        if type(item) is slice:
            slice_str = "{}:{}".format(item.start if item.start else '',
                                       item.stop if item.stop is not None and item.stop < 2**31 else "")
            if item.step:
                slice_str += ":{}".format(item.step)
            title = rich_string("{}[{}]".format(self.title.text, slice_str),
                                "{}[{}]".format(self.title.html, slice_str))
            return FileList(list.__getitem__(self, item),
                            path=self.fullpath, extcol=self._extcol, showpath=self._showpath,
                            sort=self._sort,
                            title=title, parent=self._parent)
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
        return FileList(content=content, path=self.path, sort=None, showpath=showpath, title="")

    def filter(self, conditional, title=None):
        self._load()
        name = title or getattr(conditional, '__name__') or str(conditional)
        title = "{}, [filter: {}]".format(self._title, name)
        return FileList([f for f in self if conditional(f)],
                        path=self.fullpath, extcol=self._extcol, showpath=self._showpath,
                        sort=None,
                        title=title, parent=self._parent)


    def sort(self, opt="dxnt"):
        self._load()
        title = "{}, [sort: {}]".format(self._title, opt)
        return FileList(FileBase.sort_list(self, opt),
                        path=self.fullpath, extcol=self._extcol, showpath=self._showpath,
                        sort=opt,
                        title=title, parent=self._parent)

    def _typed_subset(self, filetype, title):
        if os.path.samefile(self.fullpath, radiopadre.ROOTDIR):
            title = self.title + " [{}]".format(title)
        else:
            title = " [{}]".format(title)
        return FileList([f for f in self if type(f) is filetype], path=self.fullpath, title=title,
                        parent=self, sort=self._sort)

    @property
    def dirs(self):
        from .datadir import DataDir
        if self._dirs is None:
            self._dirs = self._typed_subset(DataDir, title="Subdirectories")
        return self._dirs

    @property
    def fits(self):
        from .fitsfile import FITSFile
        if self._fits is None:
            # make separate lists of fits files and image files
            self._fits = self._typed_subset(FITSFile, title="FITS files")
        return self._fits

    @property
    def images(self):
        from .imagefile import ImageFile
        if self._images is None:
            self._images = self._typed_subset(ImageFile, title="Images")
        return self._images

    @property
    def tables(self):
        from .casatable import CasaTable
        if self._tables is None:
            self._tables = self._typed_subset(CasaTable, title="Tables")
        return self._tables

    @property
    def html(self):
        from .htmlfile import HTMLFile
        if self._html_files is None:
            self._html_files = self._typed_subset(HTMLFile, title="HTML files")
        return self._html_files


