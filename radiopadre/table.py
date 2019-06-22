from IPython.display import HTML, Image, display

from radiopadre.render import DisplayableItem, rich_string, render_url, TransientMessage

_NULL_CELL = rich_string("")

class Table(DisplayableItem):
    def __init__ (self, items, preamble=None, postscript=None):
        self._data = {}
        self._nrow = len(items)
        self._ncol = 0

        for irow,row in enumerate(items):
            self._ncol = max(len(row), self._ncol)
            for icol,item in enumerate(row):
                if item is None:
                    item = _NULL_CELL
                elif type(item) is str:
                    item = rich_string(item)
                elif not isinstance(item, DisplayableItem):
                    item = rich_string(str(item))
                self._data[irow, icol] = item

        self._preamble = rich_string(preamble or "")
        self._postscript = rich_string(postscript or "")

    def _get_cell_text(self, irow, icol):
        return self._data.get((irow, icol), _NULL_CELL).render_text()

    def _get_cell_html(self, irow, icol):
        return self._data.get((irow, icol), _NULL_CELL).render_html_thumbnail()

    def render_text(self, *args, **kw):
        cells = {(irow,icol): self._get_cell_text(irow, icol) for irow in range(self._nrow) for icol in range(self._ncol)}

        colwidth = [max([len(cells[irow,icol]) for irow in range(self._nrow)]) for icol in range(self._ncol)]

        text = self._preamble.text

        for irow in range(self._nrow):
            text += " ".join(["{value:{width}}".format(value=cells[irow, icol], width=colwidth[icol])
                                   for icol in range(self._ncol)]) + "\n"

        return text + self._postscript.text

    def render_html(self, *args, **kw):
        html = self._preamble.html
        html += """<table style="border: 0px; text-align: left">\n"""

        for irow in range(self._nrow):
            html += """<tr style = "border: 0px; text-align: left">\n"""
            for icol in range(self._ncol):
                cell_html = self._get_cell_html(irow, icol)
                html +=  """    <td style = "border: 0px; text-align: left">{}</td>""".format(cell_html)
            html += """</tr>\n"""

        html += "</table>\n" + self._postscript.html

        return html



