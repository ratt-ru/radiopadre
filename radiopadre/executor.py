from concurrent.futures import ThreadPoolExecutor
import os
from . import settings
from iglesia.utils import message, debug

_executor = None
_executor_ncpu_settings = 0

def ncpu():
    ncpu = settings.gen.ncpu
    if ncpu < 1:
        ncpu = len(os.sched_getaffinity(0))
        if settings.gen.max_ncpu and settings.gen.max_ncpu < ncpu:
            ncpu = settings.gen.max_ncpu
        ncpu = max(ncpu, 1)
    return ncpu

def executor():
    """
    Returns executor object. Initializes one if not ready (or if ncpu has changed)
    """
    global _executor, _executor_ncpu_settings

    ncpu_settings = (settings.gen.ncpu, settings.gen.max_ncpu)

    if _executor is not None and ncpu_settings != _executor_ncpu_settings:
        debug("ncpu has changed, shutting down old executor")
        _executor.shutdown(wait=True)
        _executor = None

    if _executor is None:
        nw = ncpu()
        debug(f"starting new ThreadPoolExecutor with {nw} workers")
        _executor_ncpu_settings = ncpu_settings
        _executor = ThreadPoolExecutor(max_workers=nw)

    return _executor
