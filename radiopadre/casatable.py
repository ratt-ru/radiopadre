import os.path
from collections import OrderedDict
import itertools
import numpy as np

import radiopadre
from radiopadre import casacore_tables
from .file import FileBase
from .filelist import FileList
from .render import render_table, rich_string, render_status_message, render_error, TransientMessage



class CasaTable(radiopadre.file.FileBase):
    """

    """
    def __init__(self, name, table=None, title=None, parent=None, **kwargs):
        """

        :param args:
        :param kwargs:
        """
        self._error = self._dir_obj = None
        self._table = table
        self._subtables_obj = None
        self._parent = parent
        radiopadre.file.FileBase.__init__(self, name, title=title)


    @property
    def table(self):
        if self._table is not None:
            return self._table
        if casacore_tables is None:
            return RuntimeError("no casacore.tables installed")
        try:
            tab = casacore_tables.table(self.fullpath, ack=False)
            return tab
        except Exception, exc:
            return exc

    def _scan_impl(self):
        radiopadre.file.FileBase._scan_impl(self)
        self._dir_obj = None
        tab = self.table
        if isinstance(tab, Exception):
            msg = "CasaTable error: {}".format(tab)
            self.description = self.size = self._error = rich_string(msg, render_status_message(msg, 'yellow'))
        else:
            self.nrows = tab.nrows()
            self.rownumbers = tab.rownumbers()
            self.columns = tab.colnames()
            self.keywords = tab.getkeywords()
            self._subtables = list(tab.getsubtables())
            self._error = None
            self.size = "{} rows, {} cols".format(self.nrows, len(self.columns))
            self.description = "{} rows, {} columns, {} keywords, {} subtables".format(
                                self.nrows, len(self.columns), len(self.keywords), len(self._subtables))
            # make attributes for each column
            for name in tab.colnames():
                def getcol(start=0, nrow=-1, incr=1, col=name):
                    return self.table.getcol(col, start, nrow, incr)
                while hasattr(self, name):
                    name = name + "_"
                setattr(self, name, getcol)

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
            subdict[attr] = subtab = CasaTable(subtab)
            setattr(self, attr, subtab)
        return subtab

    @property
    def dir(self):
        from .datadir import DataDir
        if self._dir_obj is None:
            self._dir_obj = DataDir(self.fullpath)
        return self._dir_obj

    @property
    def subtables(self):
        if not self._subtables_obj:
            for name, subtab in self._subtables_dict.items():
                if isinstance(subtab, str):
                    self._subtables_dict[name] = CasaTable(subtab,)
                    setattr(self, name, subtab)
            self._subtables_obj = FileList(self._subtables_dict.values(),
                                            path=self.fullpath, extcol=False, showpath=False,
                                            classobj=CasaTable,
                                            parent=self._parent or self)
        return self._subtables_obj

    def _render_epoch(self, epoch, format):
        pass

    def _render_direction(self, direction, format):
        pass

    def _render_quantity(self, value, units, format):
        """
        Helper method. Renders a quantity (values with units) to a string

        :param value:   list of values
        :param units:   list of units
        :param format:
        :return:
        """
        import casacore.quanta
        if type(value) is np.ndarray:
            value = value.flatten()
        else:
            value = [value]
        if format:
            if format[0] == "%":
                return format%tuple(value)
            elif format[0] == "{":
                return format.format(*value)
        # >1 unit: include in render
        if type(units) is not str:
            qqs = [casacore.quanta.quantity(x, unit).formatted(format or '') for x, unit in zip(value, itertools.cycle(units))]
        else:
            qqs = [casacore.quanta.quantity(x, units).formatted(format or '') for x in value]
            single_unit = all([qq.endswith(units) for qq in qqs])
            if single_unit:
                qqs = [qq[:-len(units)].strip() for qq in qqs]
        return " ".join(qqs)

    @staticmethod
    def _slice_to_text(slc):
        """Helper function to convert an index (slice, int, or list of ints) into a string"""
        if type(slc) is slice:
            txt = "{}:{}".format('' if slc.start is None else slc.start, '' if slc.stop is None else slc.stop)
            if slc.step is not None:
                txt += ":{}".format(slc.step)
            return txt
        elif type(slc) is list:
            return ",".join(map(str, slc))
        else:
            return str(slc)

    @staticmethod
    def _parse_column_argument(arg, for_what):
        """Helper function to parse a column argument.
        Returns tuple of slicer, description, format"""
        colformat = None
        if arg is True or arg is None:
            return None, None, None
        elif type(arg) is str:
            return None, None, arg
        elif type(arg) in (slice, int, list):
            slicer = [arg]
        elif type(arg) is tuple:
            slicer = [s for s in arg if type(s) is not str]
            formats = [s for s in arg if type(s) is str]
            if formats:
                colformat = formats[0]
        else:
            raise TypeError("unknown {} specifier of type {}".format(for_what, type(arg)))
        if len(slicer):
            desc = "[{}]".format(",".join(map(CasaTable._slice_to_text, slicer)))
        else:
            desc = ""
        return slicer, desc, colformat

    def render_html(self, firstrow=0, nrows=100, native=False, allcols=False, _=None, **columns):
        msg = TransientMessage("Rendering {}, please wait...".format(self.fullpath), timeout=0)

        html = self._header_html() + "\n\n"
        #       render_refresh_button(full=self._parent and self._parent.is_updated())
        tab = self.table
        if isinstance(tab, Exception):
            return html + rich_string("Error accessing table {}: {}".format(self.basename, tab))
        # if first row is not specified, and columns not specified, fall back on casacore's own HTML renderer
        if native:
            return html + tab._repr_html_()

        firstrow = firstrow or 0

        # get subset of columns to use, and slicer objects
        column_slicers = {}
        column_formats = {}
        default_slicer = default_slicer_desc = None
        # _ keyword sets up default column slicer
        if _ is not None:
            default_slicer, default_slicer_desc, _ = self._parse_column_argument(_, "default")
        # any other optional keywords put us into column selection mode
        if columns:
            column_selection = []
            for col, slicer in columns.items():
                if col in self.columns:
                    slicer, desc, colformat = self._parse_column_argument(slicer, "column {}".format(col))
                    column_formats[col] = colformat
                    column_slicers[col] = slicer, desc
                    column_selection.append(col)
                else:
                    html += render_error("No such column: {}".format(col))
        if not columns or allcols:
            column_selection = self.columns

        # else use ours
        if firstrow > nrows-1:
            return html + render_error("Starting row {} out of range".format(firstrow))
        nrows = min(self.nrows-firstrow, nrows)
        labels = ["row"] + list(column_selection)
        colvalues = {}
        styles = {}
        for icol, colname in enumerate(column_selection):
            style = None
            shape_suffix = ""
            formatter = error = None

            # figure out formatting of measures/quanta columns
            colkw = tab.getcolkeywords(colname)
            units = colkw.get("QuantumUnits", [])
            measinfo = colkw.get('MEASINFO', {})
            meastype = measinfo.get('type')

            if units:
                same_units = all([u==units[0] for u in units[1:]])
                if same_units:
                    units = units[0]
                formatter = lambda value:self._render_quantity(value, units=units, format=column_formats.get(colname))
                if same_units and meastype != 'direction':
                    labels[icol+1] += ", {}".format(units)
            try:
                colvalues[icol] = colval = tab.getcol(colname, firstrow, nrows)
                column_has_shape = type(colval) is np.ndarray and colval.ndim > 1
                if column_has_shape:
                    shape_suffix = " ({})".format("x".join(map(str, colval.shape[1:])))
            except Exception, exc:
                error = type(exc)
                colvalues[icol] = ["(err)"]*nrows
            if not error:
                # apply slicer, if specified for this column. Render error if incorrect
                if colname in column_slicers:
                    slicer, desc = column_slicers[colname]
                    slicer = [slice(None)] + slicer
                    try:
                        colvalues[icol] = colvalues[icol][tuple(slicer)]
                    except IndexError:
                        colvalues[icol] = ["index error"]*nrows
                        style = "color: red"
                        error = IndexError
                    if desc:
                        shape_suffix += " " + desc
                # else try to apply default slicer, if applicable. Retain column on error
                elif default_slicer and column_has_shape and colval.ndim > len(default_slicer):
                    slicer = [slice(None)] + default_slicer
                    try:
                        colvalues[icol] = colvalues[icol][tuple(slicer)]
                        if default_slicer_desc:
                            shape_suffix += " " + default_slicer_desc
                    except IndexError:
                        pass

            if formatter and not error:
#                try:
                colvalues[icol] = map(formatter, colvalues[icol])
#                except Exception:
#                    colvalues[icol] = ["format error"]*nrows
#                    style = "color: red"

            labels[icol+1] += shape_suffix
            if style:
                styles[labels[icol+1]] = style

        data = [[self.rownumbers[firstrow+i]] + [colvalues[icol][i] for icol,col in enumerate(column_selection)] for i in xrange(nrows)]

        html += render_table(data, labels, styles=styles, numbering=False)
        return html

    def _select_rows_columns(self, rows, columns, desc):
        tab = self.table
        if isinstance(tab, Exception):
            return self._error
        if rows is not None:
            tab = tab.selectrows(rows)
        if columns is not None:
            tab = tab.select(columns)
        return CasaTable(self.fullpath, title="{} [{}]".format(self.title, desc), table=tab)


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
        return CasaTable(self.fullpath, title="{} ({})".format(self.title, taql), table=tab)

    def __call__(self, taql, sortlist='', columns='', limit=0, offset=0):
        return self.query(taql, sortlist, columns, limit, offset)


