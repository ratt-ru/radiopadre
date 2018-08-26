import cgi
import re

import IPython.display
from IPython.display import HTML, display

import radiopadre.file
from radiopadre.render import render_title, render_url, render_preamble
from radiopadre import settings

class TextFile(radiopadre.file.FileBase):
    def _repr_html_(self):
        return self.html()

    def __str__(self):
        return "%s modified %s:\n%s" % (self.path, self.update_mtime(), self.tail(None))

    def html(self, tail=None, head=None, full=False, grep=None, fs=None):
        txt = render_preamble()
        txt += "<A HREF=%s target='_blank'>" % render_url(self.fullpath) + \
               render_title(self.path) + "</A> modified %s:" % self.update_mtime();
        head = settings.text.get(head=head)
        tail = settings.text.get(tail=tail)
        fs = settings.text.get(fs=fs)
        if not head and not tail:
            return txt
        # read file
        lines = list(enumerate(file(self.fullpath).readlines()))
        # apply regex
        if grep:
            lines = [(num,line) for num,line in lines if re.search(grep, line)]
        if len(lines) <= head + tail:
            full = True
        # display full file or not?
        if full:
            head = len(lines)
            tail = 0
        # render as table
        border_style = "1px solid black"

        def render_line(line_num, line):
            border_top = border_style if line_num == lines[0][0]+1 else "none"
            border_bottom = border_style if line_num == lines[-1][0]+1 else "none"
            border_rl = border_style if line_num != "..." else "none"
            background = "#f2f2f2" if line_num != "..." else "none"
            return """
                <DIV style="display: table-row">
                    <DIV style="display: table-cell; border-top: {border_top}; border-bottom: {border_bottom};
                                border-left: {border_rl}; padding-left: 4px; padding-right: 4px;
                                background-color: {background}">{line_num}
                    </DIV>
                    <DIV style="display: table-cell; border-top: {border_top}; border-bottom: {border_bottom};
                                border-right: {border_rl}; padding-left: 4px; padding-right: 4px"><PRE>{line}</PRE>
                    </DIV>
                </DIV>\n""".format(**locals())

        txt += """<DIV style="display: table; width: 100%; font-size: {}%">""".format(fs*100)
        if head:
            for line_num, line in lines[:head]:
                txt += render_line(line_num+1, cgi.escape(line))
        if tail:
            txt += render_line("...", "")
            line0 = len(lines)-tail
            for line_num, line in lines[line0:]:
                txt += render_line(line_num+1, cgi.escape(line))
        txt += "\n</DIV>\n"
        return txt

    def show(self, tail=None, head=None, full=False, refresh=None, **kw):
        IPython.display.display(HTML(self.html(head=head, tail=tail, full=full, fs=fs)))

    def grep(self, regex, **kw):
        """shortcut for show(grep=regex)"""
        IPython.display.display(HTML(self.html(full=True, grep=regex, **kw)))

    def head(self, num=None, **kw):
        """shortcut for show(head=num)"""
        num = num or settings.text.head or 10
        IPython.display.display(HTML(self.html(head=num, tail=0, **kw)))

    def tail(self, num=None, **kw):
        """shortcut for show(tail=num)"""
        num = num or settings.text.tail or 10
        IPython.display.display(HTML(self.html(head=0, tail=num, **kw)))

    def full(self, **kw):
        """shortcut for show(full=True)"""
        IPython.display.display(HTML(self.html(full=True, **kw)))
