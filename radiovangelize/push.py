import subprocess, os.path
import click
from omegaconf import OmegaConf

from iglesia import debug, message, warning, error

from .config import get_config, PushConfig


def get_push_config(nbdir=None):
    return get_config(nbdir).push


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
def _run_command(command, subst={}, verbose=False, output_stream=None, env=None):
    command = command.format(**subst)
    shell = command[0] == "$"
    if shell:
        args = [command[1:]]
    else:
        args = command.split()
    proc = subprocess.run(args, shell=shell, env=env,
                            stdout=subprocess.PIPE if output_stream else None, 
                            stderr=subprocess.STDOUT if output_stream else None)
    (message if verbose else debug)(f"{args[0] if len(command)>100 else command} returns {proc.returncode}")
    
    if output_stream:
        lines = proc.stdout.decode('utf-8')
        output_stream.write(lines)
        if lines and not lines.endswith("\n"):
            output_stream.write("\n")

    return proc.returncode


def list_remotes(output_stream=None, **kw):
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

    message(f"Listing of {subst['remote']}:{config.dir} follows", color="GREEN")

    return _run_command(config.list_command, subst=subst, output_stream=output_stream)


def push_notebook(path: str, output_stream=None, **kw):

    # get source manifest
    manifest_file = f"{path}.manifest"
    if not os.path.exists(manifest_file):
        error(f"Manifest {manifest_file} not found. Have you rendered the notebook?")
        return None

    manifest = open(manifest_file, "rt").read().split("\n")

    # get configuration, and add arguments 
    config = OmegaConf.merge(get_push_config(nbdir=os.path.dirname(path)), kw)

    nb_name = os.path.splitext(os.path.basename(path))[0]
    if not config.name:
        config.name = nb_name

    # form up destination name
    dest = config.name + "/"
    if config.prefix:
        dest = f"{config.prefix}-{dest}" 
    if config.dir:
        dest = f"{config.dir}/{dest}"

    # setup standard command substitutions 
    subst = _setup_subst(config, files=" ".join(manifest), dest=dest, name=nb_name, path=path)

    message(f"Pushing out notebook bundle containing {len(manifest)} files to {subst['remote']}{dest}", color="GREEN")

    message("Push configuration follows:")
    for x in OmegaConf.to_yaml(config).splitlines(): 
        message("    " + x)

    # figure out sync command
    if not config.push_command:
        if subst['remote']:
            config.push_command = f"rsync -uvzR {{files}} {{remote}}:{{dest}}"
        else:
            error("neither rsync_host nor push_command specified")
            return False
        message(f"implicit push-command is {config.push_command}")

    if not config.check_command:
        if subst['remote']:
            config.check_command = f"$ ssh {{remote}} '[[ -d {{dest}} ]]'"
        else:
            error("neither rsync_host nor check_command specified")
            return False
        message(f"implicit check-command is {config.check_command}")

    # check if destination exists
    if config.check_command:
        if not _run_command(config.check_command, subst=subst, output_stream=output_stream):
            if config.overwrite:
                warning("check-command suggests that the destination already exists, and may be overwritten.")
            else:
                error("check-command suggests that the destination already exists. Use a different name, or force overwrite.")
                return False

    retcode = _run_command(config.push_command, subst=subst, output_stream=output_stream)
    if retcode:
        error(f"push-command failed with error code {retcode}.")
        return False

    if config.post_command:
        optional = config.post_command[0] == "?"
        retcode = _run_command(config.post_command[1:] if optional else config.post_command, verbose=True,
                                subst=subst, output_stream=output_stream)
        if retcode:
            if optional:
                warning(f"post-command returns error code {retcode}, this is probably OK though.")
            else:
                error(f"post-command failed with error code {retcode}.")
                return False

    return True



