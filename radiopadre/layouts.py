import radiopadre

import os.path
from collections import OrderedDict
from IPython.display import HTML, Markdown, display
from radiopadre import render


_ALL_SECTIONS = OrderedDict()

# "Logs", "Reports", "Plots", "Obsinfo", "Images", "Caltables"


def add_section(name):
    """Adds a know section to the TOC"""
    _ALL_SECTIONS[name] = name.lower().replace(" ", "_")


def render_bookmarks_bar(current_name=None):
    bookmarks = []
    for name1, label1 in _ALL_SECTIONS.items():
        if current_name == name1:
            bookmarks.append('<b>{}<b>'.format(name1))
        else:
            bookmarks.append('<a href=#{}>{}</a>'.format(label1, name1))
    return " ".join(bookmarks)


def Title(title, sections=[]):
    """Renders a title, and registers section names for a bookmark bar"""
    if type(sections) is str:
        sections = [x.strip() for x in sections.split("|")]

    for name in sections:
        add_section(name)

    rootdir = radiopadre.ABSROOTDIR
    homedir = os.path.expanduser("~")
    if homedir[-1] != "/":
        homedir += "/"
    if rootdir.startswith(homedir):
        rootdir = rootdir[len(homedir):]

    display(HTML("""<div style="float:left; font-size: 2em; font-weight: bold; margin-top: 0.67em;">{title}</div> 
                    <div style="float: right; font-family: 'Courier New'"> {rootdir}</div>
                 """.format(**locals())))



def Section(name):
    """Renders a section heading, with a bookmarks bar"""
    global _ALL_SECTIONS
    
    if name[0] == "*":
        name = name[1:]
        refresh = render.render_refresh_button(style="font-size: 1em; padding: 1px; width: 1.5em; height: 1.5em")
        refresh = """<div style="float: left;"> {refresh} </div>""".format(**locals())
        title_style = "" 
    else:
        refresh = title_style = ""

    if name not in _ALL_SECTIONS:
        add_section(name)
    label = _ALL_SECTIONS[name]

    bookmarks = render_bookmarks_bar(name)

    code = """{refresh}
              <div style="float: left; font-size: 1.5em; font-weight: bold; {title_style}; margin-top: 0.4em;">
                <A name="{label}" />
                {name}
              </div>
              <div style="float: right;"> 
                {bookmarks} 
              </div>
           """.format(**locals())

    display(HTML(code))

