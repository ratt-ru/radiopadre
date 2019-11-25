from radiopadre.file import ItemBase, FileBase
from radiopadre.render import render_title, render_url, render_preamble, rich_string, htmlize

class NotebookFile(FileBase):
    def __init__(self, *args, **kw):
        FileBase.__init__(self, *args, **kw)

    @property
    def downloadable_url(self):
        return render_url(self.fullpath, notebook=True)


