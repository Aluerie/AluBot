"""Jishaku.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

# Must be set before jishaku is imported; some flags are read at import time.
os.environ.setdefault("JISHAKU_NO_DM_TRACEBACK", "True")
os.environ.setdefault("JISHAKU_NO_UNDERSCORE", "True")
os.environ.setdefault("JISHAKU_HIDE", "True")

from jishaku.cog import OPTIONAL_FEATURES, STANDARD_FEATURES

if TYPE_CHECKING:
    from core import Bot


class AluJishaku(*STANDARD_FEATURES, *OPTIONAL_FEATURES):
    """My subclass to main frontend class for Jishaku.

    This implements all Features and is the main entry point for Jishaku.
    """

    if TYPE_CHECKING:
        bot: Bot  # ty: ignore[invalid-mutable-override]

    __is_jishaku__: bool = True


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(AluJishaku(bot=bot))
