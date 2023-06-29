"""
The structure of folders/extensions in this project as follows:

exts/
    ext_category_folder/
        _some_ext_utils_folder/
        _some_ext_utils_file.py 
        # ^ those must start with "_" in order not to be confused with one of below:
        package_folder_ext/
            **package structure like ext**
        one_file_ext.py
    
    __init__.py  # this file
    beta.py  # special beta test ext file.
    zeta.py  # clean state of^

This particular file aims to collect those files into Tuple of extensions so end result of 
`get_extensions(test)` should be something like
>>> get_extensions(False) 
>>> (
>>>    'jishaku',
>>>    'exts.fpc.dota',
>>>    'exts.fpc.lol',
>>>    'exts.community.welcome',
>>>    ...
>>> )

where full name for usual extensions consists of the following parts `exts.ext_category.cog_name`.
"""
from __future__ import annotations

import importlib
import os
from pkgutil import iter_modules
from typing import Tuple

from base import BASE_EXTENSIONS

try:
    import _test

    TEST_EXTENSIONS = _test.TEST_EXTENSIONS
    IGNORE_TEST = _test.IGNORE_TEST
except ModuleNotFoundError:
    TEST_EXTENSIONS = tuple()
    IGNORE_TEST = True

# EXTENSIONS

EXTERNAL_EXTENSIONS = ("jishaku",)  # 3rd party extensions that don't need "exts.{x}"
IGNORED_EXTENSIONS = 'beta'  # these are ignored in main bot.

# Packages
MY_PACKAGES = tuple(module.name for module in iter_modules(path=__path__))  # , prefix=f'{__package__}.'


def get_extensions(test: bool, reload: bool = False) -> Tuple[str, ...]:
    """
    Get tuple of extensions for bot to load.

    Note that this function is a bit more robust than needed according to description above.
    This function can also catch package exts in "exts/" folder itself like `beta.py`
    or like we had cog "exts.fun" be one folder cog for a very long time (now it is "exts.fun.fun")

    Parameters
    ----------
    test: :class: `bool`
        Whenever AluBot is used or its testing version YenBot.
        Maybe this whole production/testing part can be done better.
        If reader knows better - please, teach me.
    reload: :class: `bool` = False
        If `_test` module with TEST_EXTENSIONS should be reloaded.
        Used to force reload in manual text commands like `$reload all`.
    Returns
    -------
    Tuple[str, ...]
        tuple of extensions for bot to load
    """
    if test:
        if reload:
            importlib.reload(_test)
            test_exts, ignore_test = _test.TEST_EXTENSIONS, _test.IGNORE_TEST
        else:
            test_exts, ignore_test = TEST_EXTENSIONS, IGNORE_TEST

        if not ignore_test:
            return BASE_EXTENSIONS + tuple(f'exts.{x}' if x not in EXTERNAL_EXTENSIONS else x for x in test_exts)

    # production giga-gathering option.
    all_folders = [f.name for f in os.scandir('exts') if f.is_dir() if not f.name.startswith('_')]

    ext_category_folders = [x for x in all_folders if x not in MY_PACKAGES]
    uncategorised_exts = EXTERNAL_EXTENSIONS + tuple(f'exts.{x}' for x in MY_PACKAGES if x not in IGNORED_EXTENSIONS)

    categorised_exts = tuple(
        module.name
        for sf in ext_category_folders
        for module in iter_modules(path=[f'exts/{sf}'], prefix=f'exts.{sf}.')
        if not module.name.rsplit('.', 1)[-1].startswith('_')
    )

    extensions = BASE_EXTENSIONS + uncategorised_exts + categorised_exts
    return extensions
