from IPython.display import HTML, Image, display

from radiopadre.render import RenderableElement, rich_string, render_url, TransientMessage

_NULL_CELL = rich_string("")

class Table(RenderableElement):
    def __init__ (self, items, zebra=True, align="left", cw=None, tw=None):
        self._data = {}
        self._nrow = len(items)
        self._ncol = 0
        self._tr_style = "" if zebra else "background: transparent"
        self._td_style = "align: {}".format(align)

        for irow,row in enumerate(items):
            self._ncol = max(len(row), self._ncol)
            for icol,item in enumerate(row):
                if item is None:
                    item = _NULL_CELL
                elif type(item) is str:
                    item = rich_string(item)
                elif not isinstance(item, RenderableElement):
                    item = rich_string(str(item))
                self._data[irow, icol] = item

        # work out column widths
        if cw is None:
            self.col_width = {}
        elif type(cw) is dict:
            self.col_width = cw
        else:
            if len(cw) != self._ncol:
                raise ValueError("number of elements in width must match number of columns")
            self.col_width = {i: w for i, w in enumerate(cw)}
        # if any column widths are set, set table width
        if tw is None:
            # set to 100% if any column width is set explicitly to a string
            if any([type(w) is str for w in self.col_width.values()]):
                tw = 1
            # else set to sum of fractional widths
            else:
                tw = sum([w for w in self.col_width.values() if type(w) is float])
        self.tab_width = tw

    def _get_cell_text(self, irow, icol):
        return self._data.get((irow, icol), _NULL_CELL).render_text()

    def _get_cell_html(self, irow, icol, context, **kw):
        return self._data.get((irow, icol), _NULL_CELL).render_html(context=context, **kw)

    def render_text(self, **kw):
        cells = {(irow,icol): self._get_cell_text(irow, icol) for irow in range(self._nrow) for icol in range(self._ncol)}

        colwidth = [max([len(cells[irow,icol]) for irow in range(self._nrow)]) for icol in range(self._ncol)]

        text = ""

        for irow in range(self._nrow):
            text += " ".join(["{value:{width}}".format(value=cells[irow, icol], width=colwidth[icol])
                                   for icol in range(self._ncol)]) + "\n"

        return text

    def render_html(self, context=None, **kw):
        if self.tab_width:
            if type(self.tab_width) in (int, float):
                tab_width = "width: {:.1%}".format(self.tab_width)
            else:
                tab_width = "width: {}".format(self.tab_width)
        else:
            tab_width = ""
        html = """<table style="border: 0px; text-align: left; {}">\n""".format(tab_width)

        for irow in range(self._nrow):
            html += """<tr style = "border: 0px; text-align: left; {}">\n""".format(self._tr_style)
            for icol in range(self._ncol):
                w = self.col_width.get(icol, "auto")
                if type(w) in (int, float):
                    w = "{:.0%}".format(w)
                cell_html = self._get_cell_html(irow, icol, context)
                html +=  """    <td style = "border: 0px; vertical-align: top; width: {}; {}">{}</td>""".format(
                                    w, self._td_style, cell_html)
            html += """</tr>\n"""

        html += "</table>\n"

        return html



def tabulate(items, ncol=0, mincol=0, maxcol=8, **kw):

    # if items is a list of lists, invoke Table directly
    if all([type(row) is list for row in items]):
        return Table(items, **kw)

    # else treat as flat list and break up into rows

    N = len(items)
    if not ncol:
        ncol = max(mincol, min(maxcol, N))

    itemlist = list(items)
    tablerows = []

    while itemlist:
        tablerows.append(itemlist[:ncol])
        del itemlist[:ncol]

    return Table(tablerows, **kw)
