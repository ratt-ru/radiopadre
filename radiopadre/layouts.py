import radiopadre

import os.path
from collections import OrderedDict
from IPython.display import HTML, Markdown, display
from radiopadre import render

_ALL_SECTIONS = OrderedDict()

logo_image = ''
icon_image = ''

init_html = """
"""

def add_section(name):
    """Adds a know section to the TOC"""
    _ALL_SECTIONS[name] = name.lower().replace(" ", "_")


def render_bookmarks_bar(label, name):
    """Renders a bookmarks bar with all available sections"""
    ## note that this relies on document.radiopadre.add_section() above to populate each bookmark bar
    return f"""
        <div>
            <a name="{label}" /> 
            <div class="rp-section-bookmarks" data-name="{name}" data-label="{label}"></div>
        </div>
        <script type="text/javascript">
            document.radiopadre.add_section();
        </script>
    """
    

def Title(title, sections=[], logo=None, logo_width=0, logo_padding=8, icon=None, icon_width=None):
    """Renders a title.
    
    sections: deprecated, used to be used for pre-registering section names for the bookmark bars, but this is now built
    automatically.
    """
    # if type(sections) is str:
    #     sections = [x.strip() for x in sections.split("|")]
    # for name in sections:
    #     add_section(name)

    rootdir = radiopadre.ABSROOTDIR
    homedir = os.path.expanduser("~")
    if homedir[-1] != "/":
        homedir += "/"
    if rootdir.startswith(homedir):
        rootdir = rootdir[len(homedir):]

    global logo_image, icon_image

    if logo and os.path.exists(logo):
        mw = logo_width + logo_padding
        logo_width = f" width={logo_width}" if logo_width else ""
        logo = render.render_url(logo)
        logo_image = f"""<img src="{logo}" alt="" {logo_width}></img>"""
        logo_style = f"padding-right: {logo_padding}px; vertical-align: middle; min-width: {mw}px"
    else:
        logo_style = ""

    if icon:
        icon_width = f" width={icon_width}" if icon_width else ""
        icon_image = f"""<img src="{icon}" alt="" {icon_width}></img>"""

    display(HTML(f"""
        <div class="rp-title-block" style="display: table-row; margin-top: 0.5em; width: 100%">
            <div style="display: table-cell; {logo_style}">{logo_image}</div>
            <div style="display: table-cell; vertical-align: middle; width: 100%">
                <div style="display: table; width: 100%">
                    <div style="display: table-row">
                        <div style="display: table-cell">
                            <div class="rp-notebook-title">{title}</div>
                        </div>
                    </div>
                    <div style="display: table-row;">
                        <div style="display: table-cell; width: 100%; padding-top: .2em">
                            <div class="rp-notebook-path">[{rootdir}]</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    """))



def Section(name):
    """Renders a section heading, with a bookmarks bar"""
    global _ALL_SECTIONS

    if name[0] == "*" and not radiopadre.NBCONVERT:
        name = name[1:]

        if icon_image:
            btn_style = """padding-left: 1px; padding-right: 1px;
                           border-right-width: 1px; border-left-width: 1px; 
                           border-top-width: 1px; border-bottom-width: 1px;"""
        else:
            btn_style = """padding-left: 1px; padding-right: 1px; 
                           border-right-width: 1px; border-left-width: 1px; 
                           border-top-width: 1px; border-bottom-width: 1px; 
                           width: 1.5em; height: 1.5em"""

        refresh = render.render_refresh_button(style=btn_style, content=icon_image)
        refresh = """<div style="float: left;"> {refresh} </div>""".format(**locals())
        title_style = "" 
    else:
        refresh = icon_image
        title_style = ""

    name = name.lstrip("*")

    if name not in _ALL_SECTIONS:
        add_section(name)
    label = _ALL_SECTIONS[name]

    code = render_bookmarks_bar(label, name) if not radiopadre.NBCONVERT else ""

    code += f"""
        <div style="display: table">
            <div style="display: table-row">
                <div style="display: table-cell; vertical-align: middle; padding-right: 4px">
                    {refresh}  
                </div>
                <div style="display: table-cell; vertical-align: middle; font-size: 1.5em; font-weight: bold; {title_style};">
                    {name}
                </div>
                <div style="display: table-cell;">
                </div>
            </div>
        </div>
        """


    display(HTML(code))

