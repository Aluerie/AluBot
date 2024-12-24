from __future__ import annotations

import os
from typing import TYPE_CHECKING, override

from jishaku.cog import OPTIONAL_FEATURES, STANDARD_FEATURES

from bot import AluCog, ExtCategory
from utils import const

if TYPE_CHECKING:
    from bot import AluBot

category = ExtCategory(
    name="Jishaku",
    emote=const.Emote.DankFix,
    description="Jishaku",
)


class AluJishaku(AluCog, *STANDARD_FEATURES, *OPTIONAL_FEATURES, category=category):  # type: ignore
    """My subclass to main frontend class for Jishaku.

    This implements all Features and is the main entry point for Jishaku.
    """

    __is_jishaku__: bool = True

    @override
    def cog_load(self) -> None:
        os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
        os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
        os.environ["JISHAKU_HIDE"] = "True"

    @override
    def cog_unload(self) -> None:
        pass


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    return await bot.add_cog(AluJishaku(bot=bot))
