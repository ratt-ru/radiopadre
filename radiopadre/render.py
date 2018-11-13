import math
import cgi
from collections import OrderedDict



class RichString(object):
    """
    A rich_string object contains a plain string and an HTML version of itself, and will render itself
    in a notebook front-end appropriately
    """
    def __init__(self, text, html=None):
        self._text = text
        self._html = html or "<P>{}</P>".format(text)

    @property
    def text(self):
        return self._text

    @property
    def html(self):
        return self._html

    def __str__ (self):
        return self._text

    def __repr__(self):
        return self._text

    def _repr_html_(self):
        return self._html

    def __call__(self):
        """Doing richstring() is the same as richstring"""
        return self

def rich_string(text, html=None):
    if type(text) is RichString:
        if html is not None:
            raise TypeError("can't call rich_string(RichString,html): this is a bug")
        return text
    return RichString(text, html)


def render_preamble():
    """Renders HTML preamble.
    Include this in the HTML of each cell to make sure that #NOTEBOOK_FILES# in links is correctly substituted
    """
    return """<script>document.radiopadre.fixup_hrefs()</script>"""


def render_url(fullpath, prefix="files"):
    """Converts a path relative to the notebook (i.e. kernel) to a URL that
    can be served by the notebook server, by prepending the notebook
    directory""";
    return ("/#NOTEBOOK_%s#/" % prefix.upper()) + fullpath;


def render_title(title):
    return "<b>%s</b>" % cgi.escape(title)


def render_status_message(msg, bgcolor='lightblue'):
    return "<p style='background: {};'><b>{}</b></p>".format(bgcolor, cgi.escape(msg))


def render_table(data, labels, html=set(), ncol=1, links=None,
                 header=True, numbering=True,
                 styles={},
                 actions=None,
                 preamble=OrderedDict(), postscript=OrderedDict(), div_id=None
                 ):
    if not data:
        return "no content"
    txt = "<div id='{}'>".format(div_id) if div_id else "<div>"
    for code in preamble.itervalues():
        txt += code+"\n"
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
                if ncol > 1 and icol < ncol - 1 and ilab == len(labels) - 1:
                    txt += "border-right: 1px double; padding-right: 10px"
                txt += "\">%s</th>\n" % lab
            # add dummy column for action buttons
            if actions:
                txt += "<th></th>\n"
        txt += "</tr>\n"
    # configuring the table rows, row by row
    nrow = int(math.ceil(len(data) / float(ncol)))
    for irow in range(nrow):
        txt += """<tr style="border: 0px; text-align: left; {}">\n""".format(styles.get(irow, ''))
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
                    col = cgi.escape(str(col))
                txt += """<td style="border: 0px; text-align: left; """
                if ncol > 1 and icol < ncol - 1 and i == len(datum) - 1 and not actions:
                    txt += "border-right: 1px double; padding-right: 10px"
                txt += "{}; {};".format(styles.get(labels[i], ""), styles.get((irow, labels[i]), ""))
                link = links and links[idatum][i]
                if link:
                    txt += """"><A HREF=%s target='_blank'>%s</A></td>""" % (link, col)
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
    for code in postscript.itervalues():
        txt += code+"\n"
    txt += "</div>"
    return txt


def render_refresh_button(full=False):
    """Renders a "refresh" button which re-executes the current cell.
    If full is True, a double-click will re-execute the entire notebook, and the button
    will visually indicate that this is necessary
    """
    txt = """<button %s onclick="IPython.notebook.execute_cell()"
            style="position: absolute; right: 0; top: 0;
    """;
    if full:
        title = "The underlying directories have changed so it is probably wise to " + \
                "rerun the notebook. Double-click to rerun the notebook up to and including " + \
                "this cell, or click to rerun this cell only"
        txt += """color:red;"
            title="%s" ondblclick="document.radiopadre.execute_to_current_cell();"
            >&#8635;</button>
        """ % title
    else:
        txt += """;"
            title="Click to rerun this cell and refresh its contents."
            >&#8635;</button>
        """
    return txt


