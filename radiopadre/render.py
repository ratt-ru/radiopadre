import sys
import math
import html as html_module
import os.path
from collections import OrderedDict
import uuid
import itertools

from IPython.display import display, HTML, Javascript

import radiopadre

class RenderingContext(object):
    def __init__(self):
        self.div_id = uuid.uuid4().hex
        self.preamble = OrderedDict()
        self.postscript = OrderedDict()

    def finalize_html(self, html):
        return "\n".join(itertools.chain(self.preamble.values(), [html], self.postscript.values()))

_default_rendering_context = RenderingContext()

class RenderableElement(object):
    """
    Abstract base class for an object that can render itself as text or html
    """
    def render_text(self, **kw):
        """Render text version"""
        return NotImplementedError

    def render_html(self, **kw):
        """Render full HTML version"""
        return NotImplementedError

    def __str__(self):
        return self.render_text()

    def _repr_pretty_(self, p, cycle):
        """
        Implementation for the pretty-print method. Default uses render_text().
        """
        if not cycle:
            p.text(self.render_text())

    def _repr_html_(self, *args, **kw):
        """
        Internal method called by Jupyter to get an HTML rendering of an object.
        """
        context = kw.get('context') or RenderingContext()
        return context.finalize_html(self.render_html(context=context, **kw))

    def _rendering_proxy(self, method, name, arg0=None, **kw):
        return RenderingProxy(self, method, name, arg0=arg0, kwargs=kw.copy())

    def show(self, *args, **kw):
        display(HTML(self._repr_html_(*args, **kw)))



class RenderingProxy(RenderableElement):
    def __init__(self, elem, method, name, arg0=None, kwargs={}):
        self._elem = elem
        self._name = name
        self._method = method
        self._kw = kwargs
        self._arg0 = arg0

    def __call__(self, *args, **kwargs):
        kw = self._kw.copy()
        kw.update(kwargs)

        # check single argument
        if self._arg0:
            if args:
                if len(args) > 1:
                    raise TypeError("at most one non-keyword argument expected in call to {}()")
                kw[self._arg0] = args[0]

        return RenderingProxy(self._elem, self._method, self._name, arg0=self._arg0, kwargs=kw)

    def render_text(self):
        return self._elem.render_text()

    def render_html(self, **kwargs):
        kw = self._kw.copy()
        kw.update(kwargs)
        html = getattr(self._elem, self._method)(**kw)
        if isinstance(html, RenderableElement):
            return html.render_html(**kw)
        else:
            return html

class RichString(RenderableElement):
    """
    A rich_string object contains a plain string and an HTML version of itself, and will render itself
    in a notebook front-end appropriately
    """
    def __init__(self, text, html=None, bold=False, element=None, element_class=None, styles={}):
        self._text = text ## python2: text.encode("utf-8"), in 3 it's already unicode
        if html:
            self._html = html
        else:
            text = text.encode("ascii", "xmlcharrefreplace").decode()  # python3 adds decode
            if bold:
                element = "B"
            if (styles or element_class) and not element:
                element = "DIV"
            if element:
                class_str = "" if not element_class else f"class='{element_class}'"
                style_str = ""
                # process style directives
                for key, value in styles.items():
                    # "fs" gets special treatment
                    if key == "fs" and type(value) in {int, float}:
                        value = f"{int(value*100)}%"
                    key = self._style_aliases.get(key, key.replace('_', '-'))
                    style_str += f"{key}:{value}; "
                # form up HTML
                style_str = style_str and f'style="{style_str}"'
                self._html = f"<{element} {class_str} {style_str}>{text}</{element}>"
            else:
                self._html = text

    # this dictionary maps elements of the styles dict above to CSS styles
    _style_aliases = dict(fs="font-size")

    def copy(self):
        return RichString(self._text, self._html)

    @property
    def text(self):
        return self._text

    @property
    def html(self):
        return self._html

    def __nonzero__(self):
        return bool(self.text)

    def __bool__(self):
        return bool(self.text)

    def __repr__(self):
        return self._text

    def render_text(self, **kw):
        return self.text

    def render_html(self, **kw):
        return self._html

    def __call__(self):
        """Doing richstring() is the same as richstring"""
        return self

    def __add__(self, other):
        if type(other) is RichString:
            return RichString(self.text + other.text, self.html + other.html)
        else:
            return RichString(self.text + str(other), self.html + html_module.escape(str(other)))

    def __iadd__ (self, other):
        if type(other) is RichString:
            self._text += other.text
            self._html += other.html
        else:
            self._text += str(other)
            self._html += str(other)
        return self

    def prepend(self, other):
        if type(other) is RichString:
            self._text = other.text + self._text
            self._html = other.html + self._html
        else:
            other = str(other)
            self._text = other + self._text
            self._html = other + self._html
        return self


def htmlize(text):
    if text is None:
        return ''
    elif type(text) is RichString:
        return text.html
    else:
        return text.encode("ascii", "xmlcharrefreplace").decode()
#    else:
#        return unicode(str(text), "utf-8").encode("ascii", "xmlcharrefreplace")
    # elif type(text) is unicode:
    #     return text.encode("ascii", "xmlcharrefreplace")
    # else:
    #     return unicode(str(text), "utf-8").encode("ascii", "xmlcharrefreplace")

def rich_string(text, html=None, div_class=None, bold=False):
    if text is None:
        return RichString('', html, bold=bold)
    elif type(text) is RichString:
        if html is not None:
            raise TypeError("can't call rich_string(RichString,html): this is a bug")
        return text
    return RichString(text, html, bold=bold, element_class=div_class)


def Text(text, **styles):
    """Returns text rendered in HTML"""
    return RichString(text, styles=styles)

def Bold(text, **styles):
    """Returns text rendered in boldface in HTML"""
    return RichString(text, element="B", styles=styles)

def Italic(text, **styles):
    """Returns text rendered in italic in HTML"""
    return RichString(text, element="I", styles=styles)

def ColText(text, color="red", **styles):
    """Returns text rendered in italic in HTML"""
    styles['color'] = color
    return RichString(text, styles=styles)

def render_preamble():
    """Renders HTML preamble.
    Include this in the HTML of each cell to make sure that #NOTEBOOK_FILES# in links is correctly substituted
    """
    return ""
    # return """<script>document.radiopadre.fixup_hrefs()</script>"""


def render_url(fullpath, notebook=False): # , prefix="files"):
    """Converts a path relative to the notebook (i.e. kernel) to a URL that
    can be served by the notebook server, by prepending the notebook
    directory"""
    if fullpath.startswith('http://'):
        url = fullpath
    else:
        url = (radiopadre.FILE_URL_ROOT if not notebook else radiopadre.NOTEBOOK_URL_ROOT) + fullpath
    # print "{} URL is {}".format(fullpath, url)
    return url

#    return ("/#NOTEBOOK_%s#/" % prefix.upper()) + fullpath;


def render_title(title):
    if title:
        return title.html if type(title) is RichString else Bold(title).html
    return ''

def render_error(message):
    return "<SPAN style='color: red'><P>{}</P></SPAN>".format(htmlize(message))


def show_exception(message, exc_class=RuntimeError):
    display(HTML(render_error(message)))
    return exc_class(message)


def render_status_message(msg, bgcolor='lightblue'):
    return "<SPAN style='background: {};'><B>{}</B></SPAN>".format(bgcolor, htmlize(msg))


def show_table(data, **kw):
    display(HTML(render_table(data, **kw)))


def render_table(data, labels=None, html=set(), ncol=1, links=None,
                 header=True, numbering=True,
                 styles={}, tooltips={},
                 actions=None,
                 context=None
                 ):
    if not data:
        return "no content"
    if labels is None:
        labels = ["col{}".format(i) for i in range(len(data[0]))]
        header = False
    txt = "<div id='{}'>".format(context.div_id) if context else "<div>"

    txt += """<table style="border: 1px; text-align: left; {}">""".format(styles.get("TABLE",""))
    if header:
        txt += """<tr style="border: 0px; border-bottom: 1px double; text-align: center">"""
        # ncol refers to single or dual-column
        for icol in range(ncol):
            # add header for row numbers
            if numbering:
                txt += """<th style="border: 0px; border-bottom: 1px double; text-align: center">#</th>"""
            # add headers for every data column
            for ilab, lab in enumerate(labels):
                txt += """<th style="text-align: center; border: 0px; border-bottom: 1px double;"""
                if ncol > 1 and icol < ncol - 1 and ilab == len(labels) - 1 and not actions:
                    txt += "border-right: 1px double; padding-right: 10px"
                txt += "\">%s</th>\n" % lab
            # add dummy column for action buttons
            if actions:
                if ncol > 1 and icol < ncol - 1:
                    txt += """<th style="border-right: 1px double;"></th>\n"""
                else:
                    txt += """<th></th>\n"""
        txt += "</tr>\n"
    # configuring the table rows, row by row
    nrow = int(math.ceil(len(data) / float(ncol)))
    for irow in range(nrow):
        txt += """<tr style="border: 0px; text-align: left; line-height=.8em; {}">\n""".format(styles.get(irow, ''))
        for icol, idatum in enumerate(range(irow, len(data), nrow)):
            datum = data[idatum]    
            # data is a list containing (name,extension,size and modification date) for files
            # or (name,number,...) for directories
            if numbering:
                txt += """<td style="border: 0px; {}; {}">{}</td>""".format(
                    styles.get("#", ""),
                    styles.get((irow, "#"), ""),
                    idatum)
            for i, col in enumerate(datum):
                if type(col) is RichString:
                    col = col.html
                elif not str(col).upper().startswith("<HTML>") and not i in html and not labels[i] in html:
                    col = html_module.escape(str(col))
                tooltip = tooltips.get((irow, labels[i]),"")
                if tooltip:
                    tooltip = """title="{}" """.format(tooltip)
                txt += """<td {}style="border: 0px; text-align: left; """.format(tooltip)
                if ncol > 1 and icol < ncol - 1 and i == len(datum) - 1 and not actions:
                    txt += "border-right: 1px double; padding-right: 10px"
                txt += "{}; {};".format(styles.get(labels[i], ""), styles.get((irow, labels[i]), ""))
                link = links and links[idatum][i]
                if link:
                    txt += """"><A HREF='%s' target='_blank'>%s</A></td>""" % (link, col)
                else:
                    txt += """">%s</td>""" % col

            # render actions, if supplied
            if actions:
                if ncol > 1 and icol < ncol - 1:
                    txt += """<td style="white-space: nowrap; border-right: 1px double;">"""
                else:
                    txt += """<td style="white-space: nowrap; {}">"""
                if actions[idatum]:
                    txt += """{}</td>""".format(actions[idatum])
                else:
                    txt += """</td>"""
        txt += """</tr>\n"""
    txt += "</table>"
    txt += "</div>"

    return context.finalize_html(txt) if context else txt

class TransientMessage(object):
    """
    Displays a transient message in the current cell.

    Usage: create object. Message will disappear after a timeout (if set), or after the object is deleted.
    """
    last_message_id = None
    #default_backgrounds = dict(blue='rgba(173,216,230,0.8)', red='rgba(255,255,224,0.8)')
    default_backgrounds = dict(blue='rgba(255,255,240,0.8)', red='rgba(255,255,240,0.8)')

    def __init__(self, message, timeout=2, color='blue', background=None):
        self.id = id = "message-{}".format(uuid.uuid4().hex)
        if background is None:
            background = TransientMessage.default_backgrounds.get(color, 'transparent')
        html = """
            <DIV id={id} style="color: {color}; display: inline; background-color: {background}; position: absolute; right: 0; top: 0;">&nbsp;{message}&nbsp;</DIV>
            """.format(**locals())
        self.timeout = timeout
        if timeout:
            timeout = timeout*1000
            html += """<SCRIPT type="text/javascript">
                        $('#{id}').delay({timeout}).fadeOut('slow');
                        </SCRIPT>""".format(**locals())
        # hide previous message
        if TransientMessage.last_message_id:
            html += """<SCRIPT type="text/javascript">
                        $('#{}').hide();
                        </SCRIPT>""".format(TransientMessage.last_message_id)
        TransientMessage.last_message_id = self.id
        # display
        display(HTML(html))

    def hide(self):
        display(Javascript("$('#{}').hide()".format(self.id)))
        # if TransientMessage.last_message_id == self.id:
        #     TransientMessage.last_message_id = None

    def __del__(self):
        # when None, we're shutting down, so no more HTML
        if getattr(sys, 'meta_path', None) is not None:
            try:
                display(Javascript("$('#{}').fadeOut('slow')".format(self.id)))
                self.hide()
            except AttributeError:  # can also happen on shutdown
                pass



def render_refresh_button(full=False, style="position: absolute; right: 0; top: 0;", content=None):
    """Renders a "refresh" button which re-executes the current cell.
    If full is True, a double-click will re-execute the entire notebook, and the button
    will visually indicate that this is necessary.

    If content is set, overrides the default "refresh" symbols
    """
    txt = """<button style="{}" onclick="IPython.notebook.execute_cell()""".format(style)
    content = content or "&#8635;"
    if full:
        title = "The underlying directories have changed so you might want to " + \
                "rerun the whole notebook. Double-click to rerun the notebook up to and including " + \
                "this cell, or click to rerun this cell only"
        txt += f"""color:red;"
            title="%s" ondblclick="document.radiopadre.execute_to_current_cell();"
            >{content}</button>
        """ % title
    else:
        txt += f""";"
            title="Click to rerun this cell and refresh its contents."
            >{content}</button>
        """
    return txt

_collapsible_title  = {None:"", False: "Click to collapse display", True: "Click to expand display"}


def render_titled_content(title_html, content_html, buttons_html=None, collapsed=None):
    """
    Renders a block of content with a title bar, and optional action buttons.
    If collapsed is True or False, content is collapsible.
    """
    uid = uuid.uuid4().hex

    # uncollapse everything if converting notebook
    if radiopadre.NBCONVERT:
        collapsed = None

    html = f"""<div class="rp-content-block">"""
    # strip trailing whitespace (such as \n) from title
    title_html = title_html and title_html.rstrip()

    if title_html or buttons_html:
        if buttons_html:
            buttons_html = f"""<div class="actions-container">
                                        {buttons_html}
                            </div>"""
        else:
            buttons_html = ""
        # open title bar div and button container        
        html += f"""<div class="title-bar"><div class="button-container">"""

        # insert title button, if provided
        if title_html:
            title_classes = "rp-title-button"
            if collapsed is not None:
                title_classes += " rp-collapsible"
                collapsed = bool(collapsed)
                if collapsed:  # collapsed buttons have both classes. The script below toggles "rp-collapsed" in and out
                    title_classes += " rp-collapsed"


            html += f"""<button id="btn-{uid}" type="button" 
                                        class="{title_classes}"
                                        title="{_collapsible_title[collapsed]}">
                            {title_html}
                        </button>"""

        # close title button DIV, insert action buttons, close the titlebar DIV, and add spacer
        html += f"""</div>
                    {buttons_html}
                </div>
                <div class="title-bar-spacer"></div>
                """

    # add content block, and closing DIV
    html += f"""<div id="content-{uid}" class="rp-content" style="display:{'none' if collapsed else 'table-row'}">
                        {content_html}
                </div>
            </div>"""

    # add collapsible scripts
    if title_html:
        html += f"""<script>
                    btn = document.getElementById("btn-{uid}");
                    // console.log("button classes", btn.classList)
                    if (btn.classList.contains("rp-collapsible")) {{
                        btn.addEventListener("click", function() {{
                            var content = document.getElementById("content-{uid}");
                            if (this.classList.toggle("rp-collapsed")) {{
                                content.style.display = "none";
                                this.title = "{_collapsible_title[True]}"
                            }} else {{
                                content.style.display = "table-row";
                                this.title = "{_collapsible_title[False]}"
                            }}
                        }});
                    }}
                </script>
                """

    return html
