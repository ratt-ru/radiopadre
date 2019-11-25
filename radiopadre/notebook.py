from radiopadre.file import ItemBase, FileBase
from radiopadre.render import render_title, render_url, render_preamble, rich_string, htmlize

class NotebookFile(FileBase):
    def __init__(self, *args, **kw):
        FileBase.__init__(self, *args, **kw)

    def _render_title_link(self, showpath=False, url=None, **kw):
        """Renders the name of the file, with a download link"""
        url = url or render_url(self.fullpath, notebook=True)
        name = self.path if showpath else self.name
        return "<a href='{url}' target='_blank'>{name}</a>".format(**locals())


