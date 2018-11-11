import math
import cgi
from collections import OrderedDict

#edited by me lexy
from IPython.display import display, HTML
import ipywidgets as widgets
from ipywidgets import VBox
import render,time

import radiopadre

class rich_string(object):
    def __init__(self, text, html):
        self._text = text
        self._html = html

    def __repr__(self):
        return self._text

    def _repr_html_(self):
        return self._html

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


def render_status_message(msg):
    return "<p style='background: lightblue;'><b>%s</b></p>" % cgi.escape(msg)


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
        for icol in range(ncol):
            if numbering:
                txt += """<th style="border: 0px; border-bottom: 1px double; text-align: center">#</th>"""
            for ilab, lab in enumerate(labels):
                txt += """<th style="text-align: center; border: 0px; border-bottom: 1px double;"""
                if ncol > 1 and icol < ncol - 1 and ilab == len(labels) - 1:
                    txt += "border-right: 1px double; padding-right: 10px"
                txt += "\">%s</th>\n" % lab
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
                if not str(col).upper().startswith("<HTML>") and not i in html and not labels[i] in html:
                    col = cgi.escape(str(col))
                txt += """<td style="border: 0px; text-align: left; """
                if ncol > 1 and icol < ncol - 1 and i == len(datum) - 1:
                    txt += "border-right: 1px double; padding-right: 10px"
                txt += "{}; {};".format(styles.get(labels[i], ""), styles.get((irow, labels[i]), ""))
                link = links and links[idatum][i]
                if link:
                    txt += """"><A HREF=%s target='_blank'>%s</A></td>""" % (link, col)
                else:
                    txt += """">%s</td>""" % col

            # render actions, if supplied
            if actions and actions[idatum]:
                txt += """<TD>%s</TD>""" % actions[idatum]
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


