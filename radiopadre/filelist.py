import IPython
from IPython.display import display, HTML, Javascript
import os
import fnmatch
from collections import OrderedDict
import uuid
import itertools


from .file import FileBase
from .render import render_table, render_preamble, render_refresh_button, render_url, render_title

from radiopadre import settings

class FileList(FileBase, list):
    @staticmethod
    def list_to_string(filelist):
        return "Contents of %s:\n" % filelist._title + "\n".join(
            ["%d: %s" % (i, d.path) or '.' for i, d in enumerate(filelist)])

    def __init__(self, content=None, path="", root=".", extcol=False, showpath=False,
                 classobj=None, title=None, parent=None,
                 sort="xnt"):
        self._extcol = extcol
        self._showpath = showpath
        self._classobj = classobj
        self._parent = parent
        if title:
            self._title = title
        self.nfiles = self.ndirs = 0

        FileBase.__init__(self, path, root=root)

        if content is not None:
            self._set_list(content, sort)

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
        kw.setdefault('title', self._title + " (%d file%s)" % (len(self), "s" if len(self) > 1 else ""))
        kw.setdefault('showpath', self._showpath)
        method(self, **kw)

    def render_html(self, ncol=None, **kw):
        self._load()
        html = render_preamble() + render_title("{}: {}".format(self._title, self.description)) + \
               render_refresh_button(full=self._parent and self._parent.is_updated())
        # if class object has a summary function, use that
        html_summary = getattr(self._classobj, "_html_summary", None)
        if html_summary:
            return html + html_summary(self)
        # else fall back to normal filelist
        if not self:
            return html
        # auto-set 1 or 2 columns based on filename length
        if ncol is None:
            max_ = max([len(df.basename) for df in self])
            ncol = 2 if max_ <= settings.gen.twocolumn_list_width else 1
        from .datadir import DataDir
        def ext(df):
            return df.ext+"/" if os.path.isdir(df.path) else df.ext
        if self._extcol:
            labels = "name", "ext", "", "modified"
            data = [((df.basepath if self._showpath else df.basename), ext(df),
                     df.description, df.mtime_str)
                    for df in self]
            links = [(render_url(df.fullpath), render_url(df.fullpath), None, None) for df in self]
        else:
            labels = "name", "", "modified"
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
        title = os.path.join(self._title, ",".join(accepted_patterns))
        if sort is not None:
            title += ", sort order: {}".format(sort)

        return FileList(files if accepted_patterns else list(self),
                        path=self.fullpath, root=self._root, extcol=self._extcol, showpath=self._showpath, sort=sort,
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
                        path=self.fullpath, root=self._root, extcol=self._extcol, showpath=self._showpath,
                        classobj=self._classobj,
                        title=title, parent=self._parent)

    def sort(self, opt="dxnt"):
        self._load()
        title = "{}, sort order: {}".format(self._title, sort)
        return FileList(FileBase.sort_list(self, opt),
                        path=self.fullpath, root=self._root, extcol=self._extcol, showpath=self._showpath,
                        classobj=self._classobj,
                        title=title, parent=self._parent)


