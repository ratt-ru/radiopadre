import math


def render_title(title):
    return "<b>%s</b>" % title


def render_table(data, labels, ncol=1, links=None):
    html = """<table style="border: 1px; text-align: left">
        <tr style="border: 0px; border-bottom: 1px double; text-align: center">
    """
    if not data:
        return "no content"
    for icol in range(ncol):
        html += """<th style="border: 0px; border-bottom: 1px double; text-align: center">#</th>"""
        for ilab, lab in enumerate(labels):
            html += """<th style="text-align: center; border: 0px; border-bottom: 1px double;"""
            if ncol > 1 and icol < ncol - 1 and ilab == len(labels) - 1:
                html += "border-right: 1px double; padding-right: 10px"
            html += "\">%s</th>\n" % lab
    html += "</tr>\n"
    nrow = int(math.ceil(len(data) / float(ncol)))
    for irow in range(nrow):
        html += """<tr style="border: 0px; text-align: left">\n"""
        for icol, idatum in enumerate(range(irow, len(data), nrow)):
            datum = data[idatum]
            html += """<td style="border: 0px">%d</td>""" % idatum
            for i, col in enumerate(datum):
                html += """<td style="border: 0px; """
                if ncol > 1 and icol < ncol - 1 and i == len(datum) - 1:
                    html += "border-right: 1px double; padding-right: 10px"
                link = links and links[idatum][i]
                if link:
                    html += """"><A HREF=/files/%s>%s</A></td>""" % (link, col)
                else:
                    html += """">%s</td>""" % col
        html += """</tr>\n"""
    html += "</table>"
    return html
