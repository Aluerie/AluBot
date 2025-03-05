"""CORE EXTENSIONS.

This folder contains CORE_EXTENSIONS that are meant to be loaded first.
"""
from pkgutil import iter_modules

CORE_EXTENSIONS = tuple(module.name for module in iter_modules(path=__path__, prefix="core."))
