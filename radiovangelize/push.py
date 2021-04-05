import iglesia
import subprocess, os.path, traceback
import click
from omegaconf import OmegaConf
from dataclasses import dataclass
from typing import Optional

from iglesia import debug, message, warning, error

CONFIG_FILE = "radiovangelize.yml"


@dataclass 
class PushConfig(object):
    name: Optional[str] = None               # destination notebook name. Set from notebook nanme by default
    project: Optional[str] = None            # optional project identifier which can be used to form up names
    dir: Optional[str] = None                # optional remote directory
    rsync_host: Optional[str] = None         # if set, enables pushing via rsync to a remote server
    user: Optional[str] = None               # if set, specifies non-default username
    check_command: Optional[str] = None      # if set, command to use to check if the destination exists
    push_command: Optional[str] = None       # full push command -- if set, overrides the push method specified
    post_command: Optional[str] = None       # if set, executed after a successful push
    list_command: Optional[str] = None       # if set, used to list remote destinations
    overwrite: bool = False                  # force overwrite of remote destination, if check-command says it exists


_push_config = None

def get_push_config(nbdir=None):
    global _push_config
    if _push_config is None:
        _push_config = OmegaConf.structured(PushConfig)

        # now look for configuration files in order of specificity
        configs = []
        
        def add_config(path, verbose=False):
            if not os.path.exists(path):
                debug(f"{path} doesn't exist, skipping")
                return
            if os.stat(os.path.dirname(path)).st_uid != os.getuid():
                debug(f"directory of {path} not owned by us, skipping")
                return
            if any(os.path.samefile(x, path) for x in configs):
                debug(f"{path} is already read, skipping")
                return
            global _push_config
            try:
                _push_config = OmegaConf.merge(_push_config, OmegaConf.load(path))
            except Exception as exc:
                warning(f"Error reading f{path}: {traceback.format_exc()}")
                return
            (message if verbose else debug)(f"read config from {path}")
            configs.append(path)

        # look for some standard config locations
        homedir = os.path.expanduser("~")
        add_config(os.path.join(iglesia.RADIOPADRE_DIR, CONFIG_FILE))
        add_config(os.path.join(f"{homedir}/.config", CONFIG_FILE))
        add_config(os.path.join(f"{homedir}", f".{CONFIG_FILE}"))

        # add to them some custom ones, starting from the current directory and up, as long
        # as the dir is owned by us
        nbdir = os.path.abspath(nbdir or os.getcwd())
        while os.stat(nbdir).st_uid == os.getuid() and not os.path.samefile(nbdir, homedir) and nbdir != "/":
            add_config(os.path.join(nbdir, f".{CONFIG_FILE}"), verbose=True)
            nbdir = os.path.dirname(nbdir)
        
    return _push_config



def _setup_subst(config: PushConfig, **kw):
    # set up remote address
    if config.rsync_host:
        if config.user:
            remote = f"{config.user}@{config.rsync_host}"
        else:
            remote = config.rsync_host
    else:
        remote = None

    # setup standard command substitutions 
    return dict(remote=remote, config=config, **kw)


# helper function, forms up and runs command
def _run_command(command, subst={}, verbose=False, capture_output=None):
    command = command.format(**subst)
    shell = command[0] == "$"
    if shell:
        args = [command[1:]]
    else:
        args = command.split()
    proc = subprocess.run(args, shell=shell, 
                            stdout=subprocess.PIPE if capture_output else None, 
                            stderr=subprocess.STDOUT if capture_output else None)
    (message if verbose else debug)(f"{args[0] if len(command)>100 else command} returns {proc.returncode}")
    
    if capture_output:
        capture_output(proc.stdout)

    return proc.returncode


def list_remotes(capture_output=True, **kw):
    # get configuration, and add arguments 
    config = OmegaConf.merge(get_push_config(nbdir=None), kw)

    message("Push configuration follows:")
    for x in OmegaConf.to_yaml(config).splitlines(): 
        message("    " + x)

    # setup standard command substitutions 
    subst = _setup_subst(config)

    if not config.list_command:
        error("list-command not configured")
        return None

    total_output = b""
    if capture_output:
        def _capture(output):
            total_output += output
    else:
        _capture = None

    message(f"Listing of {subst['remote']}:{config.dir} follows", color="GREEN")

    retcode = _run_command(config.list_command, subst=subst, capture_output=_capture)

    return total_output if capture_output else retcode


def push_notebook(path, capture_output=True, **kw):

    # if capturing outputs, modify message handlers
    total_output = b""
    if capture_output:
        def _capture(output):
            nonlocal total_output
            total_output += output
        def message1(output, **kw):
            global message
            nonlocal total_output
            message(output, **kw)
            total_output += f"{output}\n".encode()
        def warning1(output, **kw):
            global warning
            nonlocal total_output
            warning(output, **kw)
            total_output += f"WARNING: {output}\n".encode()
        def error1(output, **kw):
            global error
            nonlocal total_output
            error(output, **kw)
            total_output += f"ERROR: {output}\n".encode()
    else:
        _capture = None
        message1, warning1, error1 = message, warning, error

    # get source manifest
    manifest_file = f"{path}.manifest"
    if not os.path.exists(manifest_file):
        error1(f"Manifest {manifest_file} not found. Have you rendered the notebook?")
        return total_output

    manifest = open(manifest_file, "rt").read().split("\n")

    # get configuration, and add arguments 
    config = OmegaConf.merge(get_push_config(nbdir=os.path.dirname(path)), kw)

    nb_name = os.path.splitext(os.path.basename(path))[0]
    if not config.name:
        config.name = nb_name

    # form up destination name
    dest = config.name + "/"
    if config.project:
        dest = f"{config.project}-{dest}" 
    if config.dir:
        dest = f"{config.dir}/{dest}"

    # setup standard command substitutions 
    subst = _setup_subst(config, files=" ".join(manifest), dest=dest, name=nb_name, path=path)

    message1(f"Pushing out notebook bundle containing {len(manifest)} files to {subst['remote']}{dest}", color="GREEN")

    message1("Push configuration follows:")
    for x in OmegaConf.to_yaml(config).splitlines(): 
        message1("    " + x)


    # figure out sync command
    if not config.push_command:
        if subst['remote']:
            config.push_command = f"rsync -uvzR {{files}} {{remote}}:{{dest}}"
        else:
            error1("neither rsync_host nor push_command specified")
            return total_output
        message(f"implicit push-command is {config.push_command}")

    if not config.check_command:
        if subst['remote']:
            config.check_command = f"$ ssh {{remote}} '[[ -d {{dest}} ]]'"
        else:
            error1("neither rsync_host nor check_command specified")
            return total_output
        message(f"implicit check-command is {config.check_command}")


 
    # check if destination exists
    if config.check_command:
        if not _run_command(config.check_command, subst=subst, capture_output=_capture):
            if config.overwrite:
                warning1("check-command suggests that the destination already exists, and may be overwritten.")
            else:
                error1("check-command suggests that the destination already exists. Use a different name, or force overwrite.")
                return total_output

    retcode = _run_command(config.push_command, subst=subst, capture_output=_capture)
    if retcode:
        error1(f"push-command failed with error code {retcode}.")
        return total_output

    if config.post_command:
        optional = config.post_command[0] == "?"
        retcode = _run_command(config.post_command[1:] if optional else config.post_command, verbose=True,
                                subst=subst, capture_output=_capture)
        if retcode:
            if optional:
                warning1(f"post-command returns error code {retcode}, this is probably OK though.")
            else:
                error1(f"post-command failed with error code {retcode}.")

    return total_output


@click.command()
@click.option("-v", "--verbose", is_flag=True, help="enable verbose output")
@click.option("-n", "--name", type=str, default=None, help="destination name")
@click.option("-p", "--project", type=str, default=None, help="destination project name")
@click.option("-f", "--force", is_flag=True, help="force overwrite of existing destination")
@click.argument("notebook", metavar="NOTEBOOK|list")
def _push_cli(notebook, name=None, project=None, force=None, verbose=False):
    import iglesia.logger
    import logging
    
    logger = iglesia.logger.init("radiovangelize")
    if verbose:
        logger.setLevel(logging.DEBUG)

    if notebook == 'list':
        list_remotes(capture_output=False)
    else:
        push_notebook(notebook, capture_output=False, name=name, project=project, overwrite=force)


