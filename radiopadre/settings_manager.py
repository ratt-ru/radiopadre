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

    def get(self, default=None, **kw):
        if not kw:
            raise RuntimeError("Section.get() must be called with at least one keyword argument")
        retval = []
        for key, value in kw.items():
            if value is None:
                value = _BASE.get(self, key)
                if value is None:
                    value = default
            retval.append(value)
        if len(retval) == 1:
            retval = retval[0]
        return retval

    @contextmanager
    def __call__(self, **kw):
        prev_values = { key:self[key] for key in kw.keys() if key in self }
        new_values = set(kw.keys()) - set(self.keys())
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
        for key, value in self.items():
            styles[len(data)] = "background-color: white"
            data.append(("{}{}.{}".format(prefix, self._name, key), repr(value), self._docs.get(key, '')))

    def _repr_html_(self):
        from radiopadre import render
        data = []
        styles = {}
        self._repr_table(data, styles)
        styles["TABLE"] = "width: 100%"
        return render.render_table(data, ("name", "value", "description"), html={"name","description"},
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
        for sec_name, section in self._sections.items():
            if isinstance(section, Section):
                for key, value in section.items():
                    txt += "{}.{}.{} = {}\n".format(self._name, sec_name, key, repr(value))
        return txt

    def _repr_html_(self):
        from radiopadre import render
        data = []
        styles = {}
        for sec_name, section in self._sections.items():
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

        gen = self.add_section("gen", "general radiopadre settings")  # generic settings

        gen.twocolumn_list_width = 40, D("file lists will default to dual-column if all names are within this length")

        gen.timeformat = "%H:%M:%S %b %d", D("time format")
        gen.collapsible = True, D("enable collapsible displays by default")

        gen.ncpu = 0, D("number of CPU cores to use, 0 to detect automatically ")
        gen.max_ncpu = 32, D("max number of CPU cores to use (when detecting automatically)")

        files = self.add_section("files", "file settings")  # generic settings

#        files.include       = "*.jpg *.png *.fits *.txt *.log", D("filename patterns to include in the listings. If None, all files will be included")
        files.include       = None, D("filename patterns to include in the listings. If None, all files will be included")
        files.exclude       = None, D("patterns to explicitly exclude from the listings")
        files.include_dir   = None, D("subdirectory patterns to include in the listings. If None, all subdirectories will be included")
        files.exclude_dir   = None, D("subdirectory patterns to explicitly exclude from the listings")
        files.include_empty = False, D("if True, empty subdirectories will also be included.")
        files.show_hidden   = False, D("if True, hidden files and subdirectories will also be included.")


        display = self.add_section("display", "display settings, should be set up auto-magically")  # generic settings

        display.cell_width = 800, D("width of Jupyter cell output, in pixels")
        display.window_width = 1024, D("width of browser window")
        display.window_height = 768, D("height of browser window")
        display.auto_reset     = True, D("auto-reset when the browser window is resized")

        plot = self.add_section("plot", "settings for rendering of plots")

        # globally fix a plot width (in inches)
        plot.width = None, D("fix a display plot width (in inches)")
        plot.screen_dpi = 80, D("plot DPI")


        thumb = self.add_section("thumb", "settings for rendering of thumbnails")

        thumb.mincol = 2, D("minimum number of columns to display in thumbnail view")
        thumb.maxcol = 4, D("maximum number of columns to display in thumbnail view")
        thumb.width  = 0, D("default thumbnail width, 0 to set automatically")
        thumb.collapsed = None, D("if not None, makes thumbnail display collapsible")

        fits = self.add_section("fits", "settings for rendering of FITS files")

        fits.colormap = 'cubehelix', D("default FITS colormap")
        fits.scale = 'linear', D("default FITS scaling")
        fits.vmin = None, D("lower clip value")
        fits.vmax = None, D("upper clip value")

        fits.max_js9_slice = 2048, D("size of active segment for JS9 display of large images")
        fits.js9_preview_size = 1024, D("size of preview image for JS9 display of large images")

        text = self.add_section("text", "settings for rendering of text files")

        text.head = 10, D("default number of lines to show from head of file")
        text.tail = 10, D("default number of lines to show from tail of file")
        text.fs   = 0.8, D("font size for text display")

        html = self.add_section("html", "settings for rendering of HTML thumbnails")

        html.width  = 1920, D("default width of HTML canvas")
        html.height = 1024, D("default height of HTML canvas")
