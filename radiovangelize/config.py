import iglesia
import os.path, traceback
from omegaconf import OmegaConf
from dataclasses import dataclass
from typing import Optional

from iglesia import debug, message, warning, error
from omegaconf import OmegaConf
from dataclasses import dataclass
from typing import Optional


CONFIG_FILE = "radiovangelize.yml"


@dataclass 
class PushConfig(object):
    name: Optional[str] = None               # destination notebook name. Set from notebook nanme by default
    prefix: Optional[str] = None             # optional prefix identifier which can be used to form up names
    dir: Optional[str] = None                # optional remote directory
    rsync_host: Optional[str] = None         # if set, enables pushing via rsync to a remote server
    user: Optional[str] = None               # if set, specifies non-default username
    check_command: Optional[str] = None      # if set, command to use to check if the destination exists
    push_command: Optional[str] = None       # full push command -- if set, overrides the push method specified
    post_command: Optional[str] = None       # if set, executed after a successful push
    list_command: Optional[str] = None       # if set, used to list remote destinations
    overwrite: bool = False                  # force overwrite of remote destination, if check-command says it exists

@dataclass 
class VangelizeConfig(object):
    push: PushConfig = PushConfig()


_config = None

def get_config(nbdir=None):
    global _config
    if _config is None:
        _config = OmegaConf.structured(VangelizeConfig)

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
            global _config
            try:
                _config = OmegaConf.merge(_config, OmegaConf.load(path))
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
        
    return _config


