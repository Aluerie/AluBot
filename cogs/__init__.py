"""
The structure of folders/cogs in this project as follows:

cogs/
    cog_category_folder/
        _some_cog_utils_folder/
        _some_cog_utils_file.py 
        # ^ those must start with "_" in order not to be confused with one of below:
        package_folder_cog/
            **package structure like cog**
        one_file_cog.py
    
    __init__.py  # this file
    beta.py  # special beta test cog file.
    zeta.py  # clean state of^

This particular file aims to collect those files into Tuple of extensions so end result of 
`get_extensions(test)` should be something like
>>> get_extensions(False) 
>>> (
>>>    'jishaku',
>>>    'cogs.fpc.dota',
>>>    'cogs.fpc.lol',
>>>    'cogs.community.welcome',
>>>    ...
>>> )

where for usual cogs the name consists of the following parts `cogs.cog_category.cog_name`.
"""
from __future__ import annotations

import os
from pkgutil import iter_modules
from typing import Tuple

try:
    from _test import IGNORE_TEST, TEST_EXTENSIONS
except ModuleNotFoundError:
    TEST_EXTENSIONS = tuple()
    IGNORE_TEST = True

# EXTENSIONS

INITIAL_EXTENSIONS = ("jishaku",)  # these don't need "cogs.{x}"
IGNORED_EXTENSIONS = ('beta', 'zeta')  # these are ignored in main bot.

# Packages
MY_PACKAGES = tuple(module.name for module in iter_modules(path=__path__))  # , prefix=f'{__package__}.'


def get_extensions(test: bool) -> Tuple[str, ...]:
    """
    Get tuple of extensions for bot to load.

    Note that this function is a bit more robust than needed according to description above.
    This function can also catch package cogs in "cogs/" folder like beta.py
    or like we had cog "cogs.fun" be one folder cog for a very long time (now it is "cogs.fun.fun")

    Parameters
    ----------
    test: :class: `bool`
        Whenever AluBot is used or its testing version YenBot.
        Maybe this whole production/testing part can be done better.
        If reader knows better - please, teach me.

    Returns
    -------
    Tuple[str, ...]
        tuple of extensions for bot to load
    """
    if test and not IGNORE_TEST:
        return tuple(f'cogs.{x}' if x not in INITIAL_EXTENSIONS else x for x in TEST_EXTENSIONS)
    else:
        all_folders = [f.name for f in os.scandir('cogs') if f.is_dir() if not f.name.startswith('_')]

        cog_category_folders = [x for x in all_folders if x not in MY_PACKAGES]
        uncategorised_extensions = INITIAL_EXTENSIONS + tuple(
            f'cogs.{x}' for x in MY_PACKAGES if x not in IGNORED_EXTENSIONS
        )

        categorised_extensions = tuple(
            module.name
            for sf in cog_category_folders
            for module in iter_modules(path=[f'cogs/{sf}'], prefix=f'cogs.{sf}.')
            if not module.name.rsplit('.', 1)[-1].startswith('_')
        )

        extensions = uncategorised_extensions + categorised_extensions
        return extensions
