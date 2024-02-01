"""
This folder contains CORE_EXTENSIONS that are meant to be
* loaded first to eliminate some race conditions.
* loaded whenever the bot is testing or production versions since those extensions are vital for both.

Basically, "core extensions".
"""
from pkgutil import iter_modules

CORE_EXTENSIONS = tuple(module.name for module in iter_modules(path=__path__, prefix="core."))
