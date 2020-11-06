import os.path
from collections import OrderedDict
import itertools
import numpy as np
from numpy.ma import masked_array
from contextlib import contextmanager

import radiopadre
from radiopadre import casacore_tables
from radiopadre import settings
from .filelist import FileList
from .render import render_table, rich_string, render_status_message, \
    render_error, TransientMessage, render_preamble, render_titled_content



class CasaTable(radiopadre.file.FileBase):
    """

    """
    class ColumnProxy(object):
        def __init__(self, casatable, name, flagrow=False, flag=False):
            self._casatable = casatable
            self._name = name
            self._flagrow = flagrow
            self._flag = flag

        def __call__(self, start=0, nrow=-1, incr=1, flag=False):
            return self._casatable.getcol(self._name, start, nrow, incr, flagrow=flag or self._flagrow, flag=flag or self._flag)

        @staticmethod
        def _slice_to_casa(slc, row_based=True):
            """
            Helper method to convert a slice element into CASA slicing indices (which uses either
            (start, nrows, step), or (start, end, incr), depending on context)

            :param slc:         slice object or integer index
            :param row_based:   if True, return start, nrows, step. Else return start, end, step
            :return:            4-tuple of start, {nrows or end}, step, index,
                                where index is 0 if slc was an integer, or slice(None) if it was a slice
            """
            if type(slc) is int:
                if slc < 0:
                    raise IndexError("{} is not a valid table column index".format(slc))
                start = end = slc
                step = 1
            elif type(slc) is slice:
                start = 0 if slc.start is None else slc.start
                if start < 0:
                    raise IndexError("start index in {} is not valid for a table column".format(slc))
                if slc.stop is None:
                    end = -1
                else:
                    if slc.stop < start:
                        raise IndexError("end index in {} is not valid for a table column".format(slc))
                    end = slc.stop - 1
                step = 1 if slc.step is None else slc.step
                if step < 1:
                    raise IndexError("step index in {} is not valid for a table column".format(slc))
            else:
                raise IndexError("{} is not a valid table column index".format(slc))
            # convert end to nrows, unless it is set to -1
            if row_based and end >= 0:
                end = end - start + 1
            return start, end, step, (0 if type(slc) is int else slice(None))

        def __getitem__(self, item):
            if type(item) is not tuple:
                item = (item, )
            if len(item) < 1:
                raise IndexError("{} is not a valid table column index".format(item))

            # parse the index elements. First one selects rows, subsequent ones select column slice
            start, nrows, step, index = self._slice_to_casa(item[0], row_based=True)
            blc = []
            trc = []
            incr = []
            posterior_slice = [index]
            indexing_elements = [blc, trc, incr, posterior_slice]
            for slc in item[1:]:
                for i, element in enumerate(self._slice_to_casa(slc, row_based=False)):
                    indexing_elements[i].append(element)

            return self._casatable.getcol(self._name, start, nrows, step,
                                          blc or None, trc or None, incr or None,
                                          flagrow=self._flagrow, flag=self._flag)[tuple(posterior_slice)]


    def __init__(self, name, table=None, title=None, parent=None, **kwargs):
        """

        :param args:
        :param kwargs:
        """
        self._error = self._dir_obj = None
        self._table = table
        self._writeable = table and table.iswritable()
        self._num_locks = 0
        self._writeable_lock = False
        self._subtables_obj = None
        self._parent = parent
        self._dynamic_attributes = set()  # keep track of attributes added in scan_impl
        radiopadre.file.FileBase.__init__(self, name, title=title)


    @contextmanager
    def lock_table(self, write=False):
        """Context manager. Sets lock on table. For use, see examples below."""
        if casacore_tables is None:
            raise RuntimeError("no casacore.tables installed")
        # check for writability
        writable = casacore_tables.tableiswritable(self.fullpath) if self._table is None else self._writeable

        if write and not writable:
            raise IOError("table is not writable")

        # if table object is not open, we won't hold one outside of the context (and auto-locking is good enough)
        if self._table is None:
            tab = casacore_tables.table(self.fullpath, readonly=not write)
            yield tab
            tab.close()
        # if table object is open (i.e. we were created with a query or a sub-table), count locks
        else:
            # lock first time. If write-lock requested and no write lock set, lock again
            if not self._num_locks or (write and not self._writeable_lock):
                self._writeable_lock = write
                self._table.lock(write=write)
            self._num_locks += 1
            yield self._table
            # unlock
            self._num_locks -= 1
            if self._num_locks <= 0:
                self._num_locks = 0
                self._table.unlock()

    @property
    def wtable(self):
        return self.lock_table(True)

    @property
    def table(self):
        return self.lock_table(False)

    @property
    def downloadable_url(self):
        return None

    def _scan_impl(self):
        radiopadre.file.FileBase._scan_impl(self)
        self._dir_obj = None

        if casacore_tables is None:
            msg = "python-casacore not installed"
            self.description = self.size = self._error = rich_string(msg, render_status_message(msg, 'yellow'))
            return

        if self._table is None:
            self._writeable = casacore_tables.tableiswritable(self.fullpath)
            self._table = casacore_tables.table(self.fullpath, ack=False, readonly=not self._writeable, lockoptions='user')
        else:
            self._table.resync()

        with self.table as tab:
            self.nrows = tab.nrows()
            self.rownumbers = tab.rownumbers()
            self.columns = tab.colnames()
            self.keywords = tab.getkeywords()
            self._subtables = list(tab.getsubtables())
            self._error = None
            self.size = "{} rows, {} cols".format(self.nrows, len(self.columns))
            self.description = "{} rows, {} columns, {} keywords, {} subtables".format(
                                self.nrows, len(self.columns), len(self.keywords), len(self._subtables))
            flagrow = 'FLAG_ROW' in self.columns
            flagcol = 'FLAG' in self.columns

            # remove any previous dynamically-created attributes
            for attr in self._dynamic_attributes:
                if hasattr(self, attr):
                    delattr(self, attr)
            self._dynamic_attributes = set()

            # make attributes for each column
            for name in tab.colnames():
                attrname = name
                while hasattr(self, attrname):
                    attrname = attrname + "_"
                self._dynamic_attributes.add(attrname)
                setattr(self, attrname, CasaTable.ColumnProxy(self, name))
                # make _F versions for flagged columns
                flag = flagcol and (name.endswith('DATA') or name.endswith('SPECTRUM'))
                if flag or flagrow:
                    attrname = "{}_F".format(name)
                    while hasattr(self, attrname):
                        attrname = attrname + "_"
                    self._dynamic_attributes.add(attrname)
                    setattr(self, attrname, CasaTable.ColumnProxy(self, name, flagrow=flagrow, flag=flag))

            # make attributes for each subtable
            self._subtables_dict = OrderedDict()
            self._subtables_obj = None
            for path in self._subtables:
                name = os.path.basename(path)
                while hasattr(self, name):
                    name = name + "_"
                self._subtables_dict[name] = path
                self._dynamic_attributes.add(name)
                setattr(self, name, path)

    def putcol(self, colname, coldata, start=0, nrow=-1, rowincr=1, blc=None, trc=None, incr=None):
        with self.wtable as tab:
            msg = TransientMessage("Writing column {}".format(colname))
            return tab.putcol(colname, coldata, start, nrow, rowincr) if blc is None else \
                   tab.putcolslice(colname, coldata, blc, trc, incr, start, nrow, rowincr)

    def copycol(self, fromcol, tocol):
        with self.wtable as tab:
            if tocol not in tab.colnames():
                self.addcol(tocol, likecol=fromcol)
            msg = TransientMessage("Copying column {} to {}".format(fromcol, tocol))
            tab.putcol(tocol, tab.getcol(fromcol))

    def delcol(self, *columns):
        with self.wtable as tab:
            tab.removecols(columns)

    def addcol(self, colname, likecol='DATA', coltype=None):
        with self.wtable as tab:
            if colname in tab.colnames():
                raise IOError("column {} already exists".format(colname))
            msg = TransientMessage("Adding column {} (based on {})".format(colname, likecol))
            # new column needs to be inserted -- get column description from column 'like_col'
            desc = tab.getcoldesc(likecol)
            desc['name'] = colname
            desc['comment'] = desc['comment'].replace(" ", "_")  # got this from Cyril, not sure why
            dminfo = tab.getdminfo(likecol)
            dminfo["NAME"] =  "{}-{}".format(dminfo["NAME"], colname)
            # if a different type is specified, insert that
            if coltype:
                desc['valueType'] = coltype
            tab.addcols(desc, dminfo)

    def getcol(self, colname, start=0, nrow=-1, rowincr=1, blc=None, trc=None, incr=None, flagrow=False, flag=False):
        """Like standard getcol() or getcolslice() of a CASA table, but can also read a flag column to make a masked array"""
        with self.table as tab:
            msg = TransientMessage("Reading column {}".format(colname))
            coldata = tab.getcol(colname, start, nrow, rowincr) if blc is None else \
                      tab.getcolslice(colname, blc, trc, incr, start, nrow, rowincr)
            if coldata is None:
                return None
            shape = coldata.shape if type(coldata) is np.ndarray else [len(coldata)]
            fr = fl = None
            if flagrow and "FLAG_ROW" in self.columns:
                fr = tab.getcol("FLAG_ROW", start, nrow, rowincr)
                if fr.shape != (shape[0],):
                    raise ValueError("FLAG_ROW column has unexpected shape {}".format(fr.shape))
            if flag and "FLAG" in self.columns:
                fl = tab.getcol("FLAG", start, nrow, rowincr) if blc is None else \
                     tab.getcolslice("FLAG", blc, trc, incr, start, nrow, rowincr)
                if fl.shape != shape[-len(fl.shape):]:
                    raise ValueError("FLAG column has unexpected shape {}".format(fl.shape))
            if fr is not None or fl is not None:
                mask = np.zeros(shape, bool)
                if fr is not None:
                    mask[fr,...] = True
                if fl is not None:
                    mask[...,fl] = True
                return masked_array(coldata, mask)
            return coldata


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
                    self._subtables_dict[name] = CasaTable(subtab)
                    setattr(self, name, subtab)
            self._subtables_obj = FileList(self._subtables_dict.values(),
                                            path=self.fullpath, extcol=False, showpath=False,
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

    def render_html(self, firstrow=0, nrows=100, native=False, allcols=False, _=None, context=None, title=None, collapsed=None, **columns):
        with self.transient_message("Rendering {}, please wait...".format(self.fullpath)), \
                self.table as tab:
            title_html = self._header_html(title=title) + "\n\n"
            content_html = ""
            if collapsed is None and settings.gen.collapsible:
                collapsed = False
            firstrow = firstrow or 0

            if isinstance(tab, Exception):
                content_html = render_error("Error accessing table {}: {}".format(self.basename, tab))
                collapsed = None
            # empty? return
            elif not self.nrows:
                collapsed = None
            elif firstrow > self.nrows-1:
                content_html = render_error("Starting row {} out of range".format(firstrow))
                collapsed = None
            # if first row is not specified, and columns not specified, fall back on casacore's own HTML renderer
            elif native:
                content_html = tab._repr_html_()
            else:
                # get subset of columns to use, and slicer objects
                column_slicers = {}
                column_formats = {}
                default_slicer = default_slicer_desc = None
                # _ keyword sets up default column slicer
                if _ is not None:
                    default_slicer, default_slicer_desc, _ = self._parse_column_argument(_, "default")
                # any other optional keywords put us into column selection mode
                column_selection = []
                skip_columns = set()
                have_explicit_columns = False
                # build up column selection from arguments
                if columns:
                    for col, slicer in columns.items():
                        if slicer is None:
                            skip_columns.add(col)
                        else:
                            have_explicit_columns = True
                            if col in self.columns:
                                slicer, desc, colformat = self._parse_column_argument(slicer, "column {}".format(col))
                                column_formats[col] = colformat
                                column_slicers[col] = slicer, desc
                                column_selection.append(col)
                            else:
                                content_html += render_error("No such column: {}".format(col))

                # if no columns at all were selected,
                if allcols or not have_explicit_columns:
                    column_selection = [col for col in self.columns if col not in skip_columns]

                # else use ours
                nrows = min(self.nrows-firstrow, nrows)
                labels = ["row"] + list(column_selection)
                colvalues = {}
                styles = {}
                for icol, colname in enumerate(column_selection):
                    style = None
                    shape_suffix = ""
                    formatter = error = colval = None
                    column_has_shape = False

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
                    # getcol() is prone to "RuntimeError: ...  no array in row N", so explicitly ignore that and render empty column
                    try:
                        colvalues[icol] = colval = tab.getcol(colname, firstrow, nrows)
                    except RuntimeError:
                        colvalues[icol] = [""]*nrows
                        continue
                    except Exception as exc:
                        error = exc

                    if not error:
                        try:
                            colvalues[icol] = colval = tab.getcol(colname, firstrow, nrows)
                            # work around variable-shaped string columns
                            if type(colval) is dict:
                                if 'array' not in colval or 'shape' not in colval:
                                    raise TypeError("unknown column shape")
                                colvalues[icol] = colval = np.array(colval['array'], dtype=object).reshape(colval['shape'])
                            column_has_shape = type(colval) is np.ndarray and colval.ndim > 1
                            if column_has_shape:
                                shape_suffix = " ({})".format("x".join(map(str, colval.shape[1:])))
                        except Exception as exc:
                            error = exc

                    # render the value
                    if not error:
                        # apply slicer, if specified for this column. Render error if incorrect
                        if colname in column_slicers:
                            slicer, desc = column_slicers[colname]
                            slicer = [slice(None)] + slicer
                            try:
                                colvalues[icol] = colvalues[icol][tuple(slicer)]
                            except IndexError as exc:
                                error = exc
                            if desc:
                                shape_suffix += " " + desc
                        # else try to apply default slicer, if applicable. Retain column on error
                        elif default_slicer and column_has_shape and colval.ndim > len(default_slicer):
                            slicer = [Ellipsis] + default_slicer
                            try:
                                colvalues[icol] = colvalues[icol][tuple(slicer)]
                                if default_slicer_desc:
                                    shape_suffix += " " + default_slicer_desc
                            except IndexError:
                                pass

                    if formatter and not error:
                        try:
                            colvalues[icol] = list(map(formatter, colvalues[icol]))
                        except Exception as exc:
                            error = exc

                    labels[icol+1] += shape_suffix

                    # on any error, fill column with "(error)"
                    if error:
                        colvalues[icol] = ["(error)"]*nrows
                        content_html += render_error("Column {}: {}: {}".format(colname, error.__class__.__name__, str(error)))
                        style = "color: red"
                    if style:
                        styles[labels[icol+1]] = style

                data = [[self.rownumbers[firstrow+i]] + [colvalues[icol][i] for icol,col in enumerate(column_selection)] for i in range(nrows)]

                content_html += render_table(data, labels, styles=styles, numbering=False)
            return render_preamble() + \
                    render_titled_content(title_html=title_html,
                                          content_html=content_html,
                                          collapsed=collapsed)

    def _select_rows_columns(self, rows, columns, desc):
        with self.table as tab:
            if rows is not None:
                tab = tab.selectrows(rows)
            if columns is not None:
                tab = tab.select(columns)
            return CasaTable(self.fullpath, title="{} [{}]".format(self.title, desc), table=tab)

    def __getitem__(self, item):
        if self._error:
            return self._error
        if type(item) is slice:
            item = (item, )
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
                    rows.update(range(*x.indices(self.nrows)))
                    desc = "{}:{}".format("" if x.start is None else x.start,
                                          "" if (x.stop is None or x.stop > self.nrows) else x.stop)
                    if x.step is not None:
                        desc += ":{}".format(x.step)
                    descs.append(desc)
                else:
                    raise TypeError("invalid index element {} of type {}".format(x, type(x)))
            columns = ",".join(columns)
            if columns:
                descs.append(columns)
            return self._select_rows_columns(sorted(rows) if rows else None, columns, ",".join(descs))
        else:
            raise TypeError("invalid __getitem__ argument {} of type {}".format(item, type(item)))

    # def __getslice__(self, *slicer):
    #     return self[(slice(*slicer),)]

    def query(self, taql, sortlist='', columns='', limit=0, offset=0):
        if self._error:
            return self._error
        with self.table as tab0:
            tab = tab0.query(taql, sortlist=sortlist,columns=columns, limit=limit, offset=offset)
            return CasaTable(self.fullpath, title="{} ({})".format(self.title, taql),
                             table=tab)

    def __call__(self, taql, sortlist='', columns='', limit=0, offset=0):
        return self.query(taql, sortlist, columns, limit, offset)


