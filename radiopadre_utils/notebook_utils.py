import os
from IPython.display import display, Javascript, HTML


def _notebook_save_hook(model, **kwargs):
    """This hook is registered from the command line via 
        --ContentsManager.pre_save_hook
    Scrubs output before saving notebook"""
    metadata = model['content']['metadata']
    scrub = metadata.get(u'radiopadre_notebook_scrub', 1)
    author = metadata.get(u'radiopadre_notebook_author', None)
    protect = metadata.get(u'radiopadre_notebook_protect', 0)
    if protect:
        scrub = True
        if author == os.environ['USER']:
            print("Saving protected notebook since the author \"%s\" is you" % author)
        else:
            display(HTML("won't save notebook"))
            raise (
            RuntimeError, "Won't save this notebook, metadata indicates it is protected by author \"%s\"" % author)
    if not scrub:
        print("Will not scrub output")
        return
    # only run on notebooks
    if model['type'] != 'notebook':
        return
    # only run on nbformat v4
    if model['content']['nbformat'] != 4:
        return

    scrubbed = 0
    model['content']['metadata'].pop('signature', None)
    for cell in model['content']['cells']:
        scrub_cell(cell)
        scrubbed += 1

    print("Scrubbed output from %d cells" % scrubbed)


def scrub_cell(cell):
    if cell['cell_type'] != 'code':
        return
    if 'outputs' in cell:
        cell['outputs'] = []
    for field in ("prompt_number", "execution_number"):
        if field in cell:
            del cell[field]
    for field in ("execution_count",):
        if field in cell:
            cell[field] = None
