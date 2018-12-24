import IPython
from IPython.display import display, HTML, Javascript
import os
import fnmatch
from collections import OrderedDict
import uuid
import itertools


from .file import FileBase
from .render import render_table, render_preamble, render_refresh_button, render_url, render_title

import radiopadre
from radiopadre import settings

class FileList(FileBase, list):
    @staticmethod
    def list_to_string(filelist):
        return "Contents of %s:\n" % filelist._title + "\n".join(
            ["%d: %s" % (i, d.path) or '.' for i, d in enumerate(filelist)])

    def __init__(self, content=None, path="", extcol=False, showpath=False,
                 classobj=None, title=None, parent=None,
                 sort="xnt"):
        self._extcol = extcol
        self._showpath = showpath
        self._classobj = classobj
        self._parent = parent
        self._sort = sort or ""
        if title:
            self._title = title
        self.nfiles = self.ndirs = 0

        FileBase.__init__(self, path)

        if content is not None:
            self._set_list(content, sort)
            # if all content is of same type, set the classobj
            type0 = type(content[0])
            if issubclass(type0, FileBase) and not self._classobj and len(set([type(x) for x in content])) == 1:
                self._classobj = classobj = type0

        # For every _show_xxx() method defined in the class object,
        # create a corresponding self.xxx() method that maps to it
        for method in dir(classobj):
            if method.startswith("_show_"):
                func = getattr(classobj, method)
                setattr(self, method[6:], lambda func=func,**kw:self._call_collective_method(func, **kw))

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
        self._reset_summary()

    def _reset_summary(self):
        self._description = "{} files".format(self.nfiles)
        if self.ndirs:
            self._description += ", {} dirs".format(self.ndirs)
        self._summary = "{}: {}".format(self._title, self._description)

    def _call_collective_method(self, method, **kw):
        display(HTML(render_refresh_button(full=self._parent and self._parent.is_updated())))
        if not self:
            display(HTML("<p>0 files</p>"))
            return None
        kw.setdefault('title', self._title + ": %d file%s" % (len(self), "s" if len(self) > 1 else ""))
        kw.setdefault('showpath', self._showpath)
        method(self, **kw)

    def render_html(self, ncol=None, **kw):
        self._load()
        html = render_preamble() + render_title("{}: {}".format(self._title, self.description)) + \
               render_refresh_button(full=self._parent and self._parent.is_updated())

        arrow = "&uarr;" if "r" in self._sort else "&darr;"
        # find primary sort key ("d" and "r" excepted)
        sort = self._sort.replace("r", "").replace("d", "")
        primary_sort = sort and sort[0]

        # if class object has a summary function, use that
        html_summary = getattr(self._classobj, "_html_summary", None)
        if html_summary:
            return html + html_summary(self, primary_sort=primary_sort, sort_arrow=arrow)
        # else fall back to normal filelist
        if not self:
            return html
        # auto-set 1 or 2 columns based on filename length
        if ncol is None:
            max_ = max([len(df.basename) for df in self])
            ncol = 2 if max_ <= settings.gen.twocolumn_list_width else 1

        def ext(df):
            return df.ext+"/" if os.path.isdir(df.path) else df.ext

        if self._extcol:
            labels = ("{}name".format(arrow if primary_sort == "n" else ""),
                      "{}ext".format(arrow  if primary_sort == "x" else ""),
                      "{}size".format(arrow if primary_sort == "s" else ""),
                      "{}modified".format(arrow if primary_sort == "t" else ""))
            data = [((df.basepath if self._showpath else df.basename), ext(df),
                     df.description, df.mtime_str)
                    for df in self]
            links = [(render_url(df.fullpath), render_url(df.fullpath), None, None) for df in self]
        else:
            labels = (arrow+"name" if primary_sort == "n" else
                          ("name {}ext".format(arrow) if primary_sort == "x" else "name"),
                      "{}size".format(arrow if primary_sort == "s" else ""),
                      "{}modified".format(arrow if primary_sort == "t" else ""))
            data = [((df.basepath if self._showpath else df.basename) + ext(df),
                     df.description, df.mtime_str) for df in self]
            links = [(render_url(df.fullpath), None, None) for df in self]
        # get "action buttons" associated with each file
        preamble = OrderedDict()
        postscript = OrderedDict()
        div_id = uuid.uuid4().hex
        actions = [ df._action_buttons_(preamble=preamble, postscript=postscript, div_id=div_id) for df in self ]
        html += render_table(data, labels, links=links, ncol=ncol, actions=actions,
                             preamble=preamble, postscript=postscript, div_id=div_id)
        return html

    def render_text(self):
        self._load()
        return FileList.list_to_string(self)

    def _scan_impl(self):
        FileBase._scan_impl(self)
        self._reset_summary()

    # def watch(self,*args,**kw):
    #     display(HTML(render_refresh_button()))
    #     self.show_all(*args,**kw)

    def show_all(self, *args, **kw):
        display(HTML(render_refresh_button(full=self._parent and self._parent.is_updated())))
        if not self:
            display(HTML("<p>0 files</p>"))
        for f in self:
            f.show(*args, **kw)

    def __call__(self, *patterns):
        """Returns a FileList os files from this list that match a pattern. Use !pattern to invert the meaning.
        Use -flags to apply a sort order (where flags is one or more of xntr, to sort by extension, name, time, and reverse)"""
        self._load()
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
        title = self._title
        if accepted_patterns:
            if os.path.samefile(self.fullpath, radiopadre.ROOTDIR):
                title = ",".join(accepted_patterns)
            else:
                title += " ({})".format(",".join(accepted_patterns))
        if sort is not None:
            title += " [sort: {}]".format(sort)

        return FileList(files if accepted_patterns else list(self),
                        path=self.fullpath, extcol=self._extcol, showpath=self._showpath, sort=sort or self._sort,
                        classobj=self._classobj,
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

    def __getslice__(self, *slc):
        self._load()
        slice_str = ":".join([str(s) if s is not None and s < 2**31 else "" for s in slc])
        title = "{}[{}]".format(self._title, slice_str)
        return FileList(list.__getslice__(self, *slc),
                        path=self.fullpath, extcol=self._extcol, showpath=self._showpath,
                        sort=self._sort,
                        classobj=self._classobj,
                        title=title, parent=self._parent)

    def sort(self, opt="dxnt"):
        self._load()
        title = "{}, [sort: {}]".format(self._title, opt)
        return FileList(FileBase.sort_list(self, opt),
                        path=self.fullpath, extcol=self._extcol, showpath=self._showpath,
                        sort=opt,
                        classobj=self._classobj,
                        title=title, parent=self._parent)


