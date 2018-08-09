from collections import OrderedDict
from contextlib import contextmanager

_BASE = dict

class Section(_BASE):
    def __getattribute__(self, name):
        if name in self:
            return self[name]
        return _BASE.__getattribute__(self, name)

    def __setattr__(self, key, value):
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


class SettingsManager(object):
    def __init__(self, name="settings"):
        self._name = name
        self._sections = OrderedDict()

    def add_section(self, name):
        self._sections[name] = Section()
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
        for sec_name, section in self._sections.iteritems():
            if isinstance(section, Section):
                for key, value in section.iteritems():
                    name = "{}.{}.{}".format(self._name, sec_name, key)
                    data.append((name, repr(value)))
        return render.render_table(data, ("name","value"), header=False, numbering=False)

    def show(self):
        from IPython.display import display,HTML
        return display(HTML(self._repr_html_()))


class RadiopadreSettingsManager(SettingsManager):
    def __init__(self, name="settings"):
        SettingsManager.__init__(self, name=name)

        GEN = self.add_section("GEN")  # generic settings

        GEN.TWOCOLUMN_LIST_WIDTH = 20        # if all filenames in a list are <= this in length,
                                             # use two columns by default

        GEN.TIMEFORMAT = "%H:%M:%S %b %d"    # time format




        PLOT = self.add_section("PLOT")

        # globally fix a plot width (in inches)
        PLOT.WIDTH = None
        PLOT.SCREEN_DPI = 80  # screen DPI


        THUMB = self.add_section("THUMB")

        THUMB.MINCOL = 2  # default min # of columns to display in thumbnail view
        THUMB.MAXCOL = 4  # default max # of columns to display in thumbnail view


        FITS = self.add_section("FITS")

        FITS.COLORMAP = 'cubehelix'
        FITS.SCALE = 'linear'
        FITS.VMIN = None
        FITS.VMAX = None

        FITS.MAX_JS9_SLICE = 2048
