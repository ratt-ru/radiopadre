import cgi
import re

import IPython.display
from IPython.display import HTML, display

import radiopadre.file
from radiopadre.render import render_title, render_url, render_preamble, rich_string
from radiopadre import settings

class TextFile(radiopadre.file.FileBase):

    def _get_lines(self, head=0, tail=0, full=False, grep=None, slicer=None):
        """
        Applies selection keywords, and returns head and tail lines from file.

        :param tail:
        :param head:
        :param full:
        :param grep:
        :param slice:
        :return: a tuple of "head" and "tail" line lists.
                Each linelist is either None, or else is a list of (linenum,text) tuples
        """
        # no selection? Return None, None
        if not head and not tail and not full and not grep and slice is None:
            return [], []
        # read file
        lines = list(enumerate(file(self.fullpath).readlines()))
        if not full:
            # apply slice
            if slicer:
                if type(slicer) is tuple:
                    lines = lines.__getslice__(*slicer)
                elif type(slicer) is int:
                    lines = lines[slicer:slicer+1]
                else:
                    raise TypeError("invalid slice object of type {}".format(type(slicer)))
                full = True
            # apply regex if given
            if grep:
                if type(grep) is str:
                    grep = [grep]
                lines = [(num, line) for num, line in lines if any([re.search(pattern, line) for pattern in grep])]
                full = True
        if not full and len(lines) <= head + tail:
            full = True
        # display full file or not?
        if full:
            return lines, []
        head = lines[:head] if head else []
        tail = lines[-tail:] if tail else []
        return head, tail

    def render_text(self, head=None, tail=None, full=False, grep=None, slicer=None):
        txt = "{} modified {}:\n".format(self.path, self.update_mtime())
        # read file, unless head and tail is already passed in
        if type(head) is not list or type(tail) is not list:
            head = settings.text.get(head=head)
            tail = settings.text.get(tail=tail)
            head, tail = self._get_lines(head, tail, full, grep, slicer)
        # empty head and tail: return just the title
        if not head and not tail:
            return txt
        for line_num, line in head:
            txt += "{}: {}\n".format(line_num+1, line.strip())
        if tail:
            txt += "...\n"
            for line_num, line in tail:
                txt += "{}: {}\n".format(line_num + 1, line.strip())
        return txt

    def render_html(self, head=None, tail=None, full=False, grep=None, fs=None, slicer=None):
        txt = render_preamble()
        txt += "<A HREF={} target='_blank'>{}</A> modified {}:".format(render_url(self.fullpath), render_title(self.path), self.update_mtime())
        fs = settings.text.get(fs=fs)
        # read file, unless head and tail is already passed in
        if type(head) is not list or type(tail) is not list:
            head = settings.text.get(head=head)
            tail = settings.text.get(tail=tail)
            head, tail = self._get_lines(head, tail, full, grep, slicer)
        # empty head and tail: return just the title
        if not head and not tail:
            return txt

        # render as table
        border_style = "1px solid black"

        def render_line(line_num, line, firstlast):
            border_top = border_style if line_num == firstlast[0]+1 else "none"
            border_bottom = border_style if line_num == firstlast[1]+1 else "none"
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
        all_lines = head+tail
        firstlast = all_lines[0][0], all_lines[-1][0]
        for line_num, line in head:
            txt += render_line(line_num+1, cgi.escape(line), firstlast)
        if tail:
            txt += render_line("...", "", firstlast)
            for line_num, line in tail:
                txt += render_line(line_num+1, cgi.escape(line), firstlast)
        txt += "\n</DIV>\n"
        return txt

    def _render(self, head=None, tail=None, full=False, grep=None, fs=None, slicer=None):
        head, tail = self._get_lines(head, tail, full, grep, slicer)
        return rich_string(self.render_text(head, tail), self.render_html(head, tail, fs=fs))

    def grep(self, regex, **kw):
        return self._render(full=True, grep=regex, **kw)

    def head(self, num=None, **kw):
        """shortcut for show(head=num)"""
        num = num or settings.text.head or 10
        return self._render(head=num, tail=0, **kw)

    def tail(self, num=None, **kw):
        """shortcut for show(tail=num)"""
        num = num or settings.text.tail or 10
        return self._render(head=0, tail=num, **kw)

    def full(self, **kw):
        """shortcut for show(full=True)"""
        return self._render(full=True, **kw)

    def __getitem__(self, linenum):
        linenum = int(linenum)
        return self._render(slicer=linenum)

    def __getslice__(self, *slicer):
        return self._render(slicer=slicer)

    def __call__(self, *args):
        return self._render(grep=args or "*")

