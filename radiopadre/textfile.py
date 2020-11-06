import re
import io
import os.path

from radiopadre.file import ItemBase, FileBase
from radiopadre.render import render_titled_content, render_url, render_preamble, rich_string, htmlize
from radiopadre import settings
from radiopadre.table import tabulate

class NumberedLineList(ItemBase):
    def __init__ (self, enumerated_lines=[], title=None, number=True):
        """
        number: if False, do not show numbers
        """
        ItemBase.__init__(self, title=title)
        self.lines = enumerated_lines
        self._show_numbers = number

    @property
    def lines(self):
        self.rescan()
        return self._lines

    @lines.setter
    def lines(self, value):
        if type(value) is enumerate:
            value = list(value)
        if not value:
            self._lines = []
        elif type(value) is str:
            self._lines = list(enumerate(value.split("\n")))
        elif type(value) is bytes:
            self._lines = list(enumerate(value.decode().split("\n")))
        elif type(value) is list:
            if type(value[0]) is str:
                self._lines = list(enumerate(value))
            elif type(value[0]) is bytes:
                self._lines = [(i, line.decode()) for i, line in enumerate(value)]
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
                    lines = lines[slice(*slicer)]
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

    def _get_render_subset(self, head, tail, full, grep, slicer):
        """helper method for render_text() and render_html(). Returns head, tail and subtitles corresponding 
        to input arguments""" 
        subtitle = []
        if type(head) is int and head:
            subtitle.append(f"head {head}")
        if type(tail) is int and tail:
            subtitle.append(f"tail {tail}")
        if type(head) is not list or type(tail) is not list:
            self.rescan(load=True)
            head = settings.text.get(head=head)
            tail = settings.text.get(tail=tail)
            head, tail = self._get_lines(head, tail, full, grep, slicer)
        if grep:
            subtitle.append(f"grep '{grep}': {len(head)} matching lines")
        subtitle=", ".join(subtitle) if subtitle else None
        return subtitle, head, tail

    def render_text(self, head=None, tail=None, full=None, grep=None, slicer=None, title=None, number=None, **kw):
        self.rescan(load=False)
        subtitle, head, tail = self._get_render_subset(head, tail, full, grep, slicer)
        txt = self._header_text(title=title, subtitle=subtitle)
        # empty head and tail: return just the title
        if not head and not tail:
            return txt
        show_numbers = self._show_numbers if number is None else number
        format = "{0}: {1}\n" if show_numbers else "{1}\n"
        for line_num, line in head:
            txt += format.format(line_num+1, line.strip())
            # txt += "{}: {}\n".format(line_num + 1, line.encode("utf-8").strip())
        if tail:
            txt += "...\n"
            for line_num, line in tail:
                txt += format.format(line_num + 1, line.strip())
                # txt += "{}: {}\n".format(line_num + 1, line.encode("utf-8").strip())
        return txt

    def render_html(self, head=None, tail=None, full=None, grep=None, fs=None, slicer=None, 
                    title=None, number=None, collapsed=None, **kw):
        self.rescan(load=False)
        fs = settings.text.get(fs=fs)
        subtitle, head, tail = self._get_render_subset(head, tail, full, grep, slicer)
        if collapsed is None and settings.gen.collapsible:
            collapsed = False

        title_html = self._header_html(title=title, subtitle=subtitle)
        content_html = ""

        # empty head and tail: return just the title
        if not head and not tail:
            collapsed = None
        else:
            show_numbers = self._show_numbers if number is None else number

            # render as table
            border_style = "1px solid black"

            def render_line(line_num, line, firstlast, fs):
                border_top = border_style if line_num == firstlast[0] else "none"
                border_bottom = border_style if line_num == firstlast[1] else "none"
                border_rl = border_style if line_num != "..." else "none"
                background = "#f2f2f2" if line_num != "..." else "none"
                line_num_html = ""
                if show_numbers:
                    line_num_html = \
                        """<DIV style="display: table-cell; border-top: {border_top}; border-bottom: {border_bottom};
                                        border-left: {border_rl}; padding-left: 4px; padding-right: 4px;
                                        height=1em; background-color: {background}">{line_num}
                        </DIV>""".format(**locals())

                return """
                    <DIV style="display: table-row; height=1em">
                        {line_num_html}
                        <DIV style="display: table-cell; border-top: {border_top}; border-bottom: {border_bottom};
                                    height=1em; border-right: {border_rl}; padding-left: 4px; padding-right: 4px"><PRE>{line}</PRE>
                        </DIV>
                    </DIV>\n""".format(**locals())

            lh = fs*1.5
            content_html += """<DIV style="display: table; width: 100%; font-size: {fs}em; line-height: {lh}em">""".format(**locals())
            firstlast = self._lines[0][0], self._lines[-1][0]
            for line_num, line in head:
                content_html += render_line(line_num, htmlize(line), firstlast, fs=fs)
            if tail:
                content_html += render_line("&#8943;", "", firstlast, fs=fs)
                for line_num, line in tail:
                    content_html += render_line(line_num, htmlize(line), firstlast, fs=fs)
            content_html += "\n</DIV>\n"

        return render_preamble() + \
                render_titled_content(title_html=title_html,
                                        content_html=content_html,
                                        collapsed=collapsed)

    def _render_thumb_impl(self, fs=0.5, head=None, tail=None, **kw):
        self.rescan(load=True)
        head = settings.text.get(head=head)
        tail = settings.text.get(tail=tail)
        head, tail = self._get_lines(head, tail)
        lh = fs*1.2
        # html = """<DIV style="display: table; width: 100%; font-size: {fs}em; line-height: {lh}em">""".format(**locals())
        #
        # def render_line(line):
        #     # background = "#f2f2f2" if line_num != "..." else "none"
        #     line = unicode(line, "utf-8").encode("ascii", "xmlcharrefreplace")
        #     return """
        #         <DIV style="display: table-row; height=1em">
        #             <DIV style="display: table-cell; height=1em; text-align: left"><PRE>{line}</PRE>
        #             </DIV>
        #         </DIV>\n""".format(**locals())
        #
        # for line_num, line in head:
        #     html += render_line(cgi.escape(line))
        # if tail:
        #     html += render_line("...")
        #     for line_num, line in tail:
        #         html += render_line(cgi.escape(line))
        # html += "\n</DIV>\n"
        # return html

        text = "".join([h[1] for h in head])
        if tail:
            text += "          &#8943;\n"
            text += "".join([t[1] for t in tail])
        text = htmlize(text)

        text = """
                <DIV style="display: table-cell; font-size: {fs}em; text-align: left; 
                        overflow: hidden; text-decoration: none !important">
                    <PRE style="white-space: pre-wrap; overflow: hidden; width=100%">{text}</PRE>
                </DIV>
            """.format(**locals())
        url = render_url(getattr(self, 'fullpath', self.path))

        return """<A HREF='{url}' target='_blank' style="text-decoration: none">{text}</A>""".format(**locals())

    def grep(self, regex, fs=None):
        return self._rendering_proxy('render_html', 'grep', grep=regex, fs=fs)

    @property
    def head(self):
        return self._rendering_proxy('render_html', 'head', arg0='head', tail=0)

    @property
    def tail(self):
        return self._rendering_proxy('render_html', 'head', arg0='tail', head=0)

    @property
    def full(self):
        return self._rendering_proxy('render_html', 'full', full=True)

    def extract(self, regexp, groups=slice(None)):
        regexp = re.compile(regexp)
        if type(groups) is int:
            groups = slice(groups, groups+1)
        elif type(groups) not in (list, tuple, slice):
            raise TypeError("invalid groups argument of type {}".format(type(groups)))
        rows = []
        for _, line in self.lines:
            match = regexp.search(line)
            if not match:
                continue
            grps = match.groups()
            if type(groups) is slice:
                rows.append([rich_string(txt) for txt in grps[groups]])
            else:
                rows.append([rich_string(grps[i]) for i in groups])
        self.message("{} lines match".format(len(rows)), timeout=2)
        return tabulate(rows)


    def __getitem__(self, item):
        self.rescan(load=True)
        if type(item) is slice:
            return NumberedLineList(self._lines[item])
        elif type(item) in (tuple, list):
            return NumberedLineList([self._lines[x] for x in item])
        else:
            return self._lines[int(item)]

    def __getslice__(self, *slicer):
        self.rescan(load=True)
        return NumberedLineList(self._get_lines(slicer=slicer)[0])

    def __call__(self, *args, **kw):
        self.rescan(load=True)
        lines = self._get_lines(grep=args)[0] if args else self.lines
        return NumberedLineList(lines, **kw)



class TextFile(FileBase, NumberedLineList):

    # do not attempt to read files above this size
    MAXSIZE = 1000000

    def __init__(self, *args, **kw):
        NumberedLineList.__init__(self, [])
        FileBase.__init__(self, *args, **kw)
        # needed to override stuff set by NumberedLineList.__init__()
        self._scan_impl()

    def _load_impl(self):
        size = os.path.getsize(self.fullpath)
        fobj = io.open(self.fullpath, "r", encoding='utf-8')
        if size <= self.MAXSIZE:
            self.lines = list(enumerate(fobj.readlines()))
            self.description = "{} lines, modified {}".format(len(self), self.mtime_str)
        else:
            self.lines = list(enumerate(fobj.readlines(self.MAXSIZE//2)))
            fobj.seek(size - self.MAXSIZE//2)
            lines1 = fobj.readlines()
            self.lines += [(num-len(lines1), line) for num, line in enumerate(lines1)]
            self.description = "large text ({}), modified {}".format(self.size, self.mtime_str)


    # def _action_buttons_(self, context, **kw):
    #     code = """
    #         <button id="" title="load text file in a new browser tab" style="font-size: 0.9em;"
    #                 onclick="window.open('{}', '_blank')">&#8663;txt</button>
    #     """.format(render_url(self.fullpath))
    #
    #     return code
    #
    #
