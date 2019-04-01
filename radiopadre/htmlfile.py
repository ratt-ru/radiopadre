from radiopadre.file import FileBase
from radiopadre.render import render_title, render_url, render_preamble, rich_string
from radiopadre import settings


class HTMLFile(FileBase):
    def __init__(self, *args, **kw):
        FileBase.__init__(self, *args, **kw)

    def render_html(self, width="99%", height=None):
        width = width or settings.display.cell_width
        height = height or settings.display.window_height
        url = render_url(self.fullpath)
        html = render_preamble() + render_title(self.title)
        html += """<IFRAME width={width} height={height} src={url}></IFRAME>""".format(**locals())
        return html
