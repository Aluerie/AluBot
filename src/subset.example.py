# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Extensions to load when `--subset-mode` CLI argument is used.

Rename this file to 'subset.py' and choose extensions you want to load when
testing version of the bot (`--subset-mode`) is running.

This is useful when we want to debug select features/modules of the bot without launching the whole thing.
Especially because some modules take quite a long time to launch or have some heavy tasks on startup.
So that would be annoying to have to wait for it to load when testing other features.
"""

SUBSET: dict[str, list[str]] = {
    "community": [
        # "moderation",
    ],
    "dev": [
        # "sync",
    ],
    "mimics": [
        "embed_fixer",
    ],
}
