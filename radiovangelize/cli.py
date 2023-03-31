import click
from .push import push_notebook, list_remotes
from .render import render_notebook

@click.group()
@click.option("-v", "--verbose", is_flag=True, help="enable verbose output.")
def cli(verbose):
    import iglesia.logger
    import logging
    
    logger = iglesia.logger.init("radiovangelize")
    if verbose:
        logger.setLevel(logging.DEBUG)


@cli.command("render",
    help="Render notebook to embedded HTML.",
    no_args_is_help=True)
@click.argument("notebook")
def _render(notebook):
    render_notebook(notebook)


@cli.command("list",
    help="List contents of configured remote destinations.")
def _list():
    list_remotes()


@cli.command("push",
    help="Push notebook bundle to a configured remote server.",
    no_args_is_help=True)
@click.option("-n", "--name", type=str, default=None, metavar="NAME", help="destination name.")
@click.option("-p", "--prefix", type=str, default=None, metavar="PREFIX", help="destination prefix.")
@click.option("-f", "--force", 'overwrite', is_flag=True, help="force overwrite of existing destination.")
@click.option("-a", "--auto-render", is_flag=True, help="enable auto-rendering if HTML version is missing.")
@click.argument("notebook")
def _push(notebook, **kw):
    push_notebook(notebook, **kw)



