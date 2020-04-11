from IPython.display import HTML, Image, display

from radiopadre.render import RenderableElement, rich_string
from collections import OrderedDict
import itertools

_NULL_CELL = rich_string("")


class Table(RenderableElement):
    def __init__ (self, items, ncol=0, zebra=True, align="left", cw="auto", tw="auto", fs=None, lh=1.5, styles={}):
        """
        ncol: if set, fixes number of columns
        """
        self._data = {}
        self._nrow = len(items)
        self._ncol = ncol
        self._styles = styles.copy()

        if zebra:
            self.set_style("table-row-even", "background", "#D0D0D0")
            self.set_style("table-row-odd", "background", "#FFFFFF")
        elif zebra is False:
            self.set_style("table-row-even", "background", "transparent")
            self.set_style("table-row-odd", "background", "transparent")
        if align:
            self.set_style("table-cell", "align", align)
            self.set_style("table-cell", "text-align", align)

        if fs is not None:
            self.set_style("table", "font-size", "{}em".format(fs))
        if lh is not None:
            self.set_style("table", "line-height", "{}em".format(lh*(fs or 1)))

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
        if cw is not None:
            if cw is "auto":
                cw = {}
            elif cw is "equal":
                cw = {i: 1/float(ncol) for i in range(ncol)}
            elif type(cw) in (list, tuple):
                cw = {i: w for i, w in enumerate(cw)}
            # set styles
            for icol in range(self._ncol):
                width = cw.get(icol, "auto")
                if type(width) in (float, int):
                    width = "{:.2%}".format(width)
                self.set_style("col{}".format(icol), "width", width)

        # if any column widths are set, set table width
        if tw is not None:
            if tw is "auto":
                # set to 100% if any column width is set explicitly to a string
                if any([type(w) is str for w in cw.values()]):
                    tw = 1
                # else set to sum of fractional widths
                elif cw and all([type(w) is float for w in cw.values()]):
                    tw = sum(cw.values())
                else:
                    tw = "auto"

            if type(tw) in (int, float):
                self.set_style("table", "width", "{:.1%}".format(tw))
            elif tw is not None:
                self.set_style("table", "width", tw)

        self.set_style("table", "border", "0px")
        self.set_style("table-cell", "vertical-align", "top")
        self.set_style("table-cell", "padding-left", "2px")
        self.set_style("table-cell", "padding-right", "2px")

    def set_style(self, element, attribute, value):
        style = self._styles.setdefault(element, OrderedDict())
        if value is None:
            if attribute in style:
                del style[attribute]
        else:
            style[attribute] = value

    def get_styles(self, *elements):
        styles = OrderedDict()
        for element in elements:
            if element in self._styles:
                styles.update(self._styles[element])
        return "; ".join(["{}: {}".format(attr, value) for attr,value in styles.items()])

    def _get_cell_text(self, irow, icol):
        return self._data.get((irow, icol), _NULL_CELL).render_text()

    def _get_cell_html(self, irow, icol, context, **kw):
        return self._data.get((irow, icol), _NULL_CELL).render_html(context=context, **kw)

    def render_text(self, **kw):
        cells = {(irow,icol): self._get_cell_text(irow, icol) for irow in range(self._nrow) for icol in range(self._ncol)}

        colwidth = [max(max([len(cells[irow,icol]) for irow in range(self._nrow)]), 1) for icol in range(self._ncol)]

        text = ""

        for irow in range(self._nrow):
            text += " ".join(["{value:{width}}".format(value=cells[irow, icol], width=colwidth[icol])
                                   for icol in range(self._ncol)]) + "\n"

        return text

    def render_html(self, context=None, **kw):
        html = """<DIV style="display: table; {}">\n""".format(self.get_styles("table"))

        for irow in range(self._nrow):
            evenodd = "table-row-odd" if irow%2 else "table-row-even"
            html += """<DIV style="display: table-row; {}">\n""".format(self.get_styles("table-row", evenodd, "row{}".format(irow)))
            for icol in range(self._ncol):
                cell_html = self._get_cell_html(irow, icol, context)
                html +=  """    <DIV style="display: table-cell; {}">{}</DIV>""".format(
                                    self.get_styles("table-cell", "col{}".format(icol), (irow, icol)), cell_html)
            html += """</DIV>\n"""

        html += "</DIV>\n"

        return html

    def __getitem__(self, item):
        rows = range(self._nrow)
        cols = range(self._ncol)

        def _apply(rows_or_cols, index):
            if type(index) is slice:
                return rows_or_cols[index]
            elif type(index) is list:
                return [rows_or_cols[x] for x in index]
            elif type(index) is int:
                return [rows_or_cols[index]]
            else:
                raise TypeError("invalid index {} of type {}".format(index, type(index)))

        if type(item) is tuple and len(item) == 2:
            rows = _apply(rows, item[0])
            cols = _apply(cols, item[1])
        else:
            rows = _apply(rows, item)

        return Table([[self._data.get((row, col), None) for col in cols] for row in rows],
                     styles=self._styles,
                     zebra=None, align=None, cw=None, tw=None, fs=None, lh=None)

#    def __getslice__(self, *slicer):
#        return self.__getitem__(slice(8slicer)


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

    return Table(tablerows, ncol=ncol, **kw)
