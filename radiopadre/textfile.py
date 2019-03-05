import cgi
import re

import IPython.display
from IPython.display import HTML, display

from radiopadre.file import ItemBase, FileBase
from radiopadre.render import render_title, render_url, render_preamble, rich_string
from radiopadre import settings


class NumberedLineList(ItemBase):
    def __init__ (self, enumerated_lines=[], title=None):
        ItemBase.__init__(self, title=title)
        self.lines = enumerated_lines

    @property
    def lines(self):
        self.rescan()
        return self._lines

    @lines.setter
    def lines(self, value):
        if not value:
            self._lines = []
        elif type(value) is str:
            self._lines = list(enumerate(value.split("\n")))
        elif type(value) is list:
            if type(value[0]) is str:
                self._lines = list(enumerate(value))
            elif type(value[0]) not in (list, tuple):
                raise TypeError("invalid lines setting")
            self._lines = value
        elif hasattr(value, 'next'):
            self._lines = list(value)
        else:
            raise TypeError("invalid lines setting of type {}".format(type(value)))
        if self.title:
            self.description = "{} lines".format(len(self))

    def __len__(self):
        self.rescan()
        return len(self._lines)

    def __iter__(self):
        self.rescan()
        for _, line in self._lines:
            yield line

    def _get_lines(self, head=0, tail=0, full=None, grep=None, slicer=None):
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
        lines = self._lines
        if not full:
            # apply slice
            if slicer:
                if type(slicer) is tuple:
                    lines = lines.__getslice__(*slicer)
                elif type(slicer) is int:
                    lines = lines[slicer:slicer+1]
                elif type(slicer) is slice:
                    lines = lines[slicer]
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

    def render_text(self, head=None, tail=None, full=None, grep=None, slicer=None, subtitle=None):
        self.rescan(load=False)
        txt = self._header_text(subtitle)
        # read file, unless head and tail is already passed in
        if type(head) is not list or type(tail) is not list:
            self.rescan(load=True)
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

    def render_html(self, head=None, tail=None, full=None, grep=None, fs=None, slicer=None, subtitle=None):
        self.rescan(load=False)
        txt = render_preamble()
        fs = settings.text.get(fs=fs)
        # read file, unless head and tail is already passed in
        if type(head) is not list or type(tail) is not list:
            self.rescan(load=True)
            head = settings.text.get(head=head)
            tail = settings.text.get(tail=tail)
            head, tail = self._get_lines(head, tail, full, grep, slicer)
        # for up title
        if grep:
            txt += "grep '{}' {}: {} matching lines".format(grep, self.title.html, len(head))
        else:
            txt += self._header_html()
        # empty head and tail: return just the title
        if not head and not tail:
            return txt

        # render as table
        border_style = "1px solid black"

        def render_line(line_num, line, firstlast, fs):
            border_top = border_style if line_num == firstlast[0] else "none"
            border_bottom = border_style if line_num == firstlast[1] else "none"
            border_rl = border_style if line_num != "..." else "none"
            background = "#f2f2f2" if line_num != "..." else "none"
            line = unicode(line, "utf-8").encode("ascii", "xmlcharrefreplace")
            return """
                <DIV style="display: table-row; height=1em">
                    <DIV style="display: table-cell; border-top: {border_top}; border-bottom: {border_bottom};
                                border-left: {border_rl}; padding-left: 4px; padding-right: 4px;
                                height=1em; background-color: {background}">{line_num}
                    </DIV>
                    <DIV style="display: table-cell; border-top: {border_top}; border-bottom: {border_bottom};
                                height=1em; border-right: {border_rl}; padding-left: 4px; padding-right: 4px"><PRE>{line}</PRE>
                    </DIV>
                </DIV>\n""".format(**locals())

        txt += """<DIV style="display: table; width: 100%; font-size: {fs}em; line-height: 1.2em">""".format(**locals())
        firstlast = self._lines[0][0], self._lines[-1][0]
        for line_num, line in head:
            txt += render_line(line_num, cgi.escape(line), firstlast, fs=fs)
        if tail:
            txt += render_line("...", "", firstlast, fs=fs)
            for line_num, line in tail:
                txt += render_line(line_num, cgi.escape(line), firstlast, fs=fs)
        txt += "\n</DIV>\n"
        return txt

    def _render(self, head=0, tail=0, full=None, grep=None, fs=None, slicer=None, title=None):
        self.rescan(load=True)
        head, tail = self._get_lines(head, tail, full, grep, slicer)
        return rich_string(self.render_text(head, tail, title=title),
                           self.render_html(head, tail, fs=fs, title=title))

    def grep(self, regex, fs=None):
        self.show(grep=regex, fs=fs, subtitle=" (grep: {})".format(regex))

    def head(self, num=None, fs=None):
        self.show(head=num, tail=0, fs=fs)

    def tail(self, num=None, fs=None):
        self.show(head=0, tail=num, fs=fs)

    def full(self, fs=None):
        self.show(full=True, fs=fs)

    def __getitem__(self, item):
        self.rescan(load=True)
        if type(item) is slice:
            return NumberedLineList(self._lines[item])
        else:
            return self._lines[int(item)]

    def __getslice__(self, *slicer):
        self.rescan(load=True)
        return NumberedLineList(self._get_lines(slicer=slicer)[0])

    def __call__(self, *args):
        self.rescan(load=True)
        return NumberedLineList(self._get_lines(grep=args)[0])



class TextFile(FileBase, NumberedLineList):
    def __init__(self, *args, **kw):
        NumberedLineList.__init__(self, [])
        FileBase.__init__(self, *args, **kw)
        # needed to override stuff set by NumberedLineList.__init__()
        self._scan_impl()

    def _load_impl(self):
        self.lines = enumerate(file(self.fullpath).readlines())
        self.description = "{} lines, modified {}".format(len(self), self.mtime_str)

