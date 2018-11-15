import os.path
from collections import OrderedDict
import numpy as np

import radiopadre
from radiopadre import casacore_tables
from .file import FileBase
from .filelist import FileList
from .render import render_table, rich_string, render_status_message, render_refresh_button, render_title



class CasaTable(radiopadre.file.FileBase):
    """

    """
    def __init__(self, name, root=".", table=None, title=None, parent=None, **kwargs):
        """

        :param args:
        :param kwargs:
        """
        self._error = self._dir_obj = None
        self._table = table
        self._subtables_obj = None
        self._parent = parent
        if title:
            self._title = title
        radiopadre.file.FileBase.__init__(self, name, root)


    @property
    def table(self):
        if self._table is not None:
            return self._table
        if casacore_tables is None:
            return RuntimeError("no casacore.tables installed")
        try:
            tab = casacore_tables.table(self.path, ack=False)
            return tab
        except Exception, exc:
            return exc

    def _scan_impl(self):
        radiopadre.file.FileBase._scan_impl(self)
        self._dir_obj = None
        tab = self.table
        if isinstance(tab, Exception):
            msg = "CasaTable error: {}".format(tab)
            self._description = self._error = self._summary = rich_string(msg, render_status_message(msg, 'yellow'))

        else:
            self.nrows = tab.nrows()
            self.rownumbers = tab.rownumbers()
            self.columns = tab.colnames()
            self.keywords = tab.getkeywords()
            self._subtables = list(tab.getsubtables())
            self._error = None
            self._description = "{} rows, {} columns".format(self.nrows, len(self.columns))
            self._summary = "{}: {} rows, {} columns, {} keywords, {} subtables".format(
                    self._title, self.nrows, len(self.columns), len(self.keywords), len(self._subtables))
            # make attributes for each subtable
            self._subtables_dict = OrderedDict()
            self._subtables_obj = None
            for path in self._subtables:
                name = os.path.basename(path)
                while hasattr(self, name):
                    name = name + "_"
                self._subtables_dict[name] = path
                setattr(self, name, path)

    def __getattribute__(self, attr):
        try:
            subdict = radiopadre.file.FileBase.__getattribute__(self, '_subtables_dict')
        except AttributeError:
            return radiopadre.file.FileBase.__getattribute__(self, attr)
        if attr not in subdict:
            return radiopadre.file.FileBase.__getattribute__(self, attr)
        subtab = subdict.get(attr)
        if isinstance(subtab, str):
            subdict[attr] = subtab = CasaTable(subtab, root=self._root)
            setattr(self, attr, subtab)
        return subtab

    @property
    def dir(self):
        from .datadir import DataDir
        if self._dir_obj is None:
            self._dir_obj = DataDir(self.fullpath, root=self._root)
        return self._dir_obj

    @property
    def subtables(self):
        if not self._subtables_obj:
            for name, subtab in self._subtables_dict.items():
                if isinstance(subtab, str):
                    self._subtables_dict[name] = CasaTable(subtab, root=self._root)
                    setattr(self, name, subtab)
            self._subtables_obj = FileList(self._subtables_dict.values(),
                                            path=self.fullpath, root=self._root, extcol=False, showpath=False,
                                            classobj=CasaTable,
                                            parent=self._parent or self)
        return self._subtables_obj

    def render_html(self, firstrow=None, nrows=100, **columns):
        html = render_title("{}: {} rows".format(self._title, self.nrows)) + \
               render_refresh_button(full=self._parent and self._parent.is_updated())
        tab = self.table
        if isinstance(tab, Exception):
            return html + rich_string("Error accessing table {}: {}".format(self.basename, tab))
        # if first row is not specified, and columns not specified, fall back on casacore's own HTML renderer
        if firstrow is None and not columns:
            return html + tab._repr_html_()

        # get subset of columns to use, and slicer objects
        column_slicers = {}
        if columns:
            column_selection = []
            for col in self.columns:
                slicer = columns.get(col, None)
                if slicer is not None:
                    if col not in self.columns:
                        raise NameError("no such column: {}".format(col))
                    column_selection.append(col)
                    if type(slicer) in (slice, int):
                        column_slicers[col] = [slicer]
                    elif type(slicer) in (list, tuple):
                        column_slicers[col] = list(slicer)
                    elif slicer is not True:
                        raise TypeError("unknown slice of type {} for column {}".format(type(slicer), col))
        else:
            column_selection = self.columns

        # else use ours
        if firstrow > nrows-1:
            return html + rich_string("Error accessing table {}: row {} out of range".format(self.basename, firstrow))
        nrows = min(self.nrows-firstrow, nrows)
        labels = ["row"] + list(column_selection)
        colvalues = {}
        for icol, colname in enumerate(column_selection):
            try:
                colvalues[icol] = tab.getcol(colname, firstrow, nrows)
            except Exception:
                colvalues[icol] = [""]*nrows
            if colname in column_slicers:
                slicer = [slice(None)] + column_slicers[colname]
                colvalues[icol] = colvalues[icol][tuple(slicer)]
        data = [[self.rownumbers[firstrow+i]] + [colvalues[icol][i] for icol,col in enumerate(column_selection)] for i in xrange(nrows)]

        # add shape hints for columns that end up with a shape
        for icol, value in enumerate(data[0]):
            if type(value) is np.ndarray and value.shape:
                labels[icol] += " ({})".format("x".join(map(str, value.shape)))

        html += render_table(data, labels, numbering=False)
        return html

    def _select_rows_columns(self, rows, columns, desc):
        tab = self.table
        if isinstance(tab, Exception):
            return self._error
        if rows is not None:
            tab = tab.selectrows(rows)
        if columns is not None:
            tab = tab.select(columns)
        return CasaTable(self.fullpath, root=self._root, title="{}[{}]".format(self._title, desc), table=tab)


    def __getitem__(self, item):
        if self._error:
            return self._error
        if type(item) is str:
            if item not in self.columns:
                raise ValueError("no such column {}".format(item))
            return self._select_rows_columns(None, item, desc=item)
        elif type(item) is tuple:
            columns = []
            descs = []
            rows = set()
            for x in item:
                if type(x) is str:
                    if x not in self.columns:
                        raise ValueError("no such column {}".format(x))
                    columns.append(x)
                elif type(x) is int:
                    rows.add(x)
                    descs.append(str(x))
                elif type(x) is slice:
                    rows.update(xrange(*x.indices(self.nrows)))
                    desc = "{}:{}".format("" if x.start is None else x.start,
                                          "" if (x.stop is None or x.stop > self.nrows) else x.stop)
                    if x.step is not None:
                        desc += ":{}".format(x.step)
                    descs.append(desc)
                else:
                    raise TypeError("invalid index element {}".format(x))
            columns = ",".join(columns)
            if columns:
                descs.append(columns)
            return self._select_rows_columns(sorted(rows) if rows else None, columns, ",".join(descs))

    def __getslice__(self, *slicer):
        return self[(slice(*slicer),)]

    def query(self, taql, sortlist='', columns='', limit=0, offset=0):
        if self._error:
            return self._error
        tab = self.table.query(taql, sortlist=sortlist,columns=columns, limit=limit, offset=offset)
        return CasaTable(self.fullpath, root=self._root, title="{}[{}]".format(self._title, taql), table=tab)

    def __call__(self, taql, sortlist='', columns='', limit=0, offset=0):
        return self.query(taql, sortlist, columns, limit, offset)


