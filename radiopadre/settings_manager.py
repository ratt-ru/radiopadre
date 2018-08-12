from collections import OrderedDict
from contextlib import contextmanager

_BASE = OrderedDict

class DocString(str):
    """Class used to identify documentation strings"""
    pass

class Section(_BASE):
    def __init__(self, name, doc=""):
        super(Section, self).__init__()
        self._name = name
        self._docstring = doc
        self._docs = {}

    def __getattribute__(self, name):
        if name[0] != "_" and name in self:
            return self[name]
        return _BASE.__getattribute__(self, name)

    def __setattr__(self, key, value):
        if key[0] == "_":
            return _BASE.__setattr__(self, key, value)
        if type(value) is tuple and len(value) == 2 and type(value[1]) is DocString:
            _BASE.__getattribute__(self, '_docs')[key] = value[1]
            value = value[0]
        self[key] = value

    def get(self,**kw):
        assert len(kw) == 1
        key, value = kw.keys()[0], kw.values()[0]
        if value is None:
            return self[key]
        else:
            return value

    @contextmanager
    def __call__(self, **kw):
        prev_values = { key:self[key] for key in kw.iterkeys() if key in self }
        new_values = set(kw.iterkeys()) - set(self.iterkeys())
        self.update(**kw)
        yield
        self.update(**prev_values)
        for key in new_values:
            del self[key]

    def __repr__(self):
        txt = ""
        for key, value in self.items():
            txt += "{}.{} = {}\n".format(self._name, key, repr(value))
        return txt

    def _repr_table(self, data, styles, prefix=""):
        styles["description"] = "padding-left: 32px"
        styles[len(data)] = "border: 0px; border-bottom: 1px double; border-top: 1px double; background-color: #f2f2f2"
        styles[len(data), "name"] = styles[len(data), "description"] = "text-align: center"
        data.append(("<B>{}{}</B>".format(prefix, self._name), '', "{}".format(self._docstring)))
        for key, value in self.iteritems():
            styles[len(data)] = "background-color: white"
            data.append(("{}{}.{}".format(prefix, self._name, key), repr(value), self._docs.get(key, '')))

    def _repr_html_(self):
        from radiopadre import render
        data = []
        styles = {}
        self._repr_table(data, styles)
        return render.render_table(data, ("name", "value", "description"), html=set(["name","description"]),
                                   styles=styles, header=False, numbering=False)

    def show(self):
        from IPython.display import display,HTML
        return display(HTML(self._repr_html_()))



class SettingsManager(object):
    def __init__(self, name="settings"):
        self._name = name
        self._sections = OrderedDict()

    def add_section(self, name, doc=""):
        self._sections[name] = Section(name, doc)
        setattr(self, name, self._sections[name])
        return self._sections[name]

    def __repr__(self):
        txt = ""
        for sec_name, section in self._sections.iteritems():
            if isinstance(section, Section):
                for key, value in section.iteritems():
                    txt += "{}.{}.{} = {}\n".format(self._name, sec_name, key, repr(value))
        return txt

    def _repr_html_(self):
        from radiopadre import render
        data = []
        styles = {}
        for sec_name, section in self._sections.iteritems():
            if isinstance(section, Section):
                section._repr_table(data, styles, self._name+".")
        return render.render_table(data, ("name", "value", "description"), html=set(["name","description"]),
                                   styles=styles, header=False, numbering=False)

    def show(self):
        from IPython.display import display,HTML
        return display(HTML(self._repr_html_()))


class RadiopadreSettingsManager(SettingsManager):
    def __init__(self, name="settings"):
        SettingsManager.__init__(self, name=name)

        D = DocString

        GEN = self.add_section("GEN", "general radiopadre settings")  # generic settings

        GEN.TWOCOLUMN_LIST_WIDTH = 20, D("file lists will default to dual-column if all names are within this length")

        GEN.TIMEFORMAT = "%H:%M:%S %b %d", D("time format")




        PLOT = self.add_section("PLOT", "settings for rendering of plots")

        # globally fix a plot width (in inches)
        PLOT.WIDTH = None, D("fix a display plot width (in inches)")
        PLOT.SCREEN_DPI = 80, D("plot DPI")


        THUMB = self.add_section("THUMB", "settings for rendering of thumbnails")

        THUMB.MINCOL = 2, D("minimum number of columns to display in thumbnail view")
        THUMB.MAXCOL = 4, D("maximum number of columns to display in thumbnail view")


        FITS = self.add_section("FITS", "settings for rendering of FITS files")

        FITS.COLORMAP = 'cubehelix', D("default FITS colormap")
        FITS.SCALE = 'linear', D("default FITS scaling")
        FITS.VMIN = None, D("sets lower value for FITS scale")
        FITS.VMAX = None, D("sets upper value for FITS scale")

        FITS.MAX_JS9_SLICE = 2048, D("maximum slice size for JS9 displays")
