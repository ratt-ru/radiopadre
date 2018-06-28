import math
import cgi


#edited by me lexy
from IPython.display import display
import ipywidgets as widgets
from ipywidgets import VBox
import render,time

#lexys
def js9_button(imag):
    
    from notebook import notebookapp
    servers = list(notebookapp.list_running_servers())
    radiopadrePort=0;

    for server in servers:
        if "radiopadre" in server['notebook_dir']:
            radiopadrePort=server['port']
            break
    #page location in jupyter
    js9_url="http://localhost:"+str(radiopadrePort)+"/files/js9-2.0.2/js9.html"
    #js9_url=render.render_url('../js9-2.0.2/js9.html')
   
    #js9 html file to edit
    url="../js9-2.0.2/js9.html"
    #Long method to 'edit the dom', bs4 prospect
    with open(url,'r') as inp:
        data=inp.readlines()

    data[42]=None
    #href='javascript:JS9.Load("http://localhost:%s/files/data/outputs/%s");'>%s</a>\n''
    data[42]='''\t\tJS9.Load("%s%s");\n'''%('../data/outputs/',imag)
    
    with open(url,'w') as outp:
        outp.writelines(data)

    url=None  
    #Find the first instance of radiopadre
    load="""<script>

                var loadIm=function (elem){
                    var emid=elem.id
                    alert(emid);
                    alert("opening image:"+emid);
                    window.open('%s','_blank');
                    JS9.Load('../data/outputs/'+emid);
                                    }
            </script>"""%(js9_url)                             
    #nutext="<td><a href=\"%s\" target=\"_blank\"><button onclick=loadIm()>JS9</button></a></td>"%(js9_url)
    nutext="<td><button onclick=loadIm(this) id='%s'>JS9</button></td>"%imag
    nutext+=load
    return nutext

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


def render_table(data, labels, html=set(), ncol=1, links=None):
    #lexy
    vbox=[]
    txt = """<table style="border: 1px; text-align: left">
        <tr style="border: 0px; border-bottom: 1px double; text-align: center">
    """
    if not data:
        return "no content"
    for icol in range(ncol):
        txt += """<th style="border: 0px; border-bottom: 1px double; text-align: center">#</th>"""
        for ilab, lab in enumerate(labels):
            txt += """<th style="text-align: center; border: 0px; border-bottom: 1px double;"""
            if ncol > 1 and icol < ncol - 1 and ilab == len(labels) - 1:
                txt += "border-right: 1px double; padding-right: 10px"
            txt += "\">%s</th>\n" % lab
    #configuring the table rows, row by row
    txt += "</tr>\n"
    nrow = int(math.ceil(len(data) / float(ncol)))
    for irow in range(nrow):
        txt += """<tr style="border: 0px; text-align: left">\n"""
        for icol, idatum in enumerate(range(irow, len(data), nrow)):
            datum = data[idatum]    
            # data is a list containing (name,extension,size and modification date) for files
            # or (name,number,...) for directories
            txt += """<td style="border: 0px">%d</td>""" % idatum   #adds the item number on the ouput list. datum, avariable with all data ie()
            for i, col in enumerate(datum):
                if not str(col).upper().startswith("<HTML>") and not i in html and not labels[i] in html:
                    col = cgi.escape(str(col))
                txt += """<td style="border: 0px; """
                if ncol > 1 and icol < ncol - 1 and i == len(datum) - 1:
                    txt += "border-right: 1px double; padding-right: 10px"
                link = links and links[idatum][i]
                if link:
                    txt += """"><A HREF=%s target='_blank'>%s</A></td>""" % (link, col)
                else:
                    txt += """">%s</td>""" % col

                    #next line added by lexyls
            if datum[1] == '.fits':
                txt+=js9_button(datum[0]+datum[1])
        #display(js9_button())
        txt += """</tr>\n"""
    txt += "</table>"
    return txt


def render_refresh_button(full=False):
    """Renders a "refresh" button which re-executes the current sell.
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


