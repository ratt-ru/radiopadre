import uuid, json

from radiopadre_kernel import TERMINAL_URL
from radiopadre import settings

from IPython.display import Javascript, HTML, IFrame, display

def new(width="99%", height=None, aspect=4/3.):
    width = width or settings.display.cell_width
    height = height or settings.display.cell_width/aspect
    
    # html = f"""<IFRAME width={width} height={height} src={TERMINAL_URL}></IFRAME>"""
    # display(HTML(html))

    display(IFrame(TERMINAL_URL, width, height))


def tabs(tablist, width="99%", height=None, aspect=4/3.):
    width = width or settings.display.cell_width
    height = height or settings.display.cell_width/aspect

    uid = uuid.uuid4().hex

    if isinstance(tablist, int):
        tablist = [f"Term {n}" for n in range(tablist)]

    tab_button_ids  = [f"{uid}-{tab}-button" for tab in tablist]
    tab_tab_ids     = [f"{uid}-{tab}-tab" for tab in tablist]

    html = f"<div width={width} height={height}>"

    for tab, tid, tid1 in zip(tablist, tab_button_ids, tab_tab_ids):
        html +=  f"""<button id="{tid}" class="rp-terminal-tablink" onclick="openTab_{uid}('{tid1}', this, 'DarkSeaGreen')">{tab}</button>\n"""

    for tab, tid in zip(tablist, tab_tab_ids):
        html += f"""
                <div id="{tid}" class="rp-terminal-tabcontent">
                    <IFRAME width={width} height={height} src={TERMINAL_URL}></IFRAME>"
                </div>
        """

    html += f"""
        </div>
        <script type='text/javascript'>
            var tab_ids_{uid} = {json.dumps(tab_tab_ids)};
            var btn_ids_{uid} = {json.dumps(tab_button_ids)};
            function openTab_{uid}(tab_id, button, color) {{
                // Hide all elements by default */
                var id;
                for (id of tab_ids_{uid}) {{
                    document.getElementById(id).style.display = "none";
                }}

                // Remove the background color of all tablinks/buttons
                for (id of btn_ids_{uid}) {{
                    document.getElementById(id).style.backgroundColor = "";
                }}

                // Show the specific tab content
                document.getElementById(tab_id).style.display = "block";

                // Add the specific color to the button used to open the tab content
                button.style.backgroundColor = color;
                }}
            // Get the element with id="defaultOpen" and click on it
            var id;
            for (id of btn_ids_{uid}.reverse()) {{
                document.getElementById(id).click()
            }}
        </script>
    """

    display(HTML(html))
