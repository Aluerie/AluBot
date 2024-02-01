from __future__ import annotations

from typing import TYPE_CHECKING

from jishaku.cog import OPTIONAL_FEATURES, STANDARD_FEATURES

from utils import AluCog, ExtCategory, const

if TYPE_CHECKING:
    from bot import AluBot

category = ExtCategory(
    name="Jishaku",
    emote=const.Emote.DankFix,
    description="Jishaku",
)


class AluJishaku(AluCog, *STANDARD_FEATURES, *OPTIONAL_FEATURES, category=category):
    """
    My subclass to main frontend class for JIshaku.

    This implements all Features and is the main entry point for Jishaku.
    """

    __is_jishaku__: bool = True


async def setup(bot: AluBot) -> None:
    return await bot.add_cog(AluJishaku(bot=bot))
