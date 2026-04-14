"""List of extensions to load.

This file contains list of extensions that the bot will load on its launch.
Useful for when we want to test just one or a few extensions without loading big extensions
that take a long time to instantiate/import (like Dota 2 ones).

Guide
-----
* Rename this file to `exts.py`.
* Write which extensions you want to run in the `EXTENSIONS_TO_LOAD` variable.
    * names should be listed with `ext.` prefix, i.e. `'ext.community.moderation'`
    * to ignore the list and use all extensions anyway - set the variable `LOAD_ALL_EXTENSIONS` to `True`

"""

EXTENSIONS_TO_LOAD: tuple[str, ...] = ("ext.dev.sync", "ext.beta")

# Change this to `True` if you want to load all extensions on the test bot anyway
LOAD_ALL_EXTENSIONS: bool = False
