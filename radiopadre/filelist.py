import IPython
from IPython.display import display, HTML, Javascript
import os
import fnmatch
from collections import OrderedDict
import uuid
import itertools


from .file import FileBase
from .render import render_table, render_preamble, render_refresh_button, render_status_message, render_url, render_title

from radiopadre import settings

class FileList(list):
    @staticmethod
    def list_to_string(filelist):
        return "Contents of %s:\n" % filelist._title + "\n".join(
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
               render_refresh_button(full=self._parent and self._parent.is_updated())
        # if call object has a summary function, use that
        html_summary = getattr(self._classobj, "_html_summary", None)
        if html_summary:
            return html + html_summary(self)
        # else fall back to normal filelist
        if not self:
            return html + ": 0 files"
        # auto-set 1 or 2 columns based on filename length
        if ncol is None:
            max_ = max([len(df.basename) for df in self])
            ncol = 2 if max_ <= settings.gen.twocolumn_list_width else 1
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
        preamble = OrderedDict()
        postscript = OrderedDict()
        div_id = uuid.uuid4().hex
        actions = [ df._action_buttons_(preamble=preamble, postscript=postscript, div_id=div_id) for df in self ]
        html += render_table(data, labels, links=links, ncol=ncol, actions=actions,
                             preamble=preamble, postscript=postscript, div_id=div_id)
        return html

    def __str__(self):
        return FileList.list_to_string(self)

    @property
    def show(self, ncol=None, **kw):
        return IPython.display.display(HTML(self._repr_html_(ncol=ncol, **kw)))

    @property
    def list(self, ncol=None, **kw):
        return IPython.display.display(HTML(self._repr_html_(ncol=ncol, **kw)))

    @property
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

    def show_all(self, *args, **kw):
        display(HTML(render_refresh_button(full=self._parent and self._parent.is_updated())))
        if not self:
            display(HTML("<p>0 files</p>"))
        for f in self:
            f.show(*args, **kw)

    def __call__(self, *patterns):
        """Returns a FileList os files from this list that match a pattern. Use !pattern to invert the meaning."""
        files = []
        for patt in itertools.chain(*[x.split() for x in patterns]):
            if patt[0] == '!':
                files += [f for f in self if not fnmatch.fnmatch((f.path if self._showpath else f.name), patt[1:])]
            else:
                files += [f for f in self if fnmatch.fnmatch((f.path if self._showpath else f.name), patt)]
        return FileList(files,
                        extcol=self._extcol, showpath=self._showpath,
                        classobj=self._classobj,
                        title=os.path.join(self._title, ",".join(patterns)), parent=self._parent)

    def thumbs(self, max=100, **kw):
        display(HTML(render_refresh_button(full=self._parent and self._parent.is_updated())))
        if not self:
            display(HTML("<p>0 files</p>"))
            return None
        kw.setdefault('title', self._title + " (%d file%s)" % (len(self), "s" if len(self) > 1 else ""))
        kw.setdefault('showpath', self._showpath)
        thumbs = getattr(self._classobj, "_show_thumbs", None)
        if thumbs:
            return thumbs(self[:max], **kw)
        display(HTML("<p>%d files. Don't know how to make thumbnails for this collection.</p>" % len(self)))

    def __getslice__(self, *slc):
        return FileList(list.__getslice__(self, *slc),
                        extcol=self._extcol, showpath=self._showpath,
                        classobj=self._classobj,
                        title="%s[%s]" % (self._title, ":".join(map(str, slc))), parent=self._parent)


