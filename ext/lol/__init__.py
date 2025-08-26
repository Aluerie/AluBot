from __future__ import annotations

from typing import TYPE_CHECKING

from utils import const

from .fpc import LolFPC

if TYPE_CHECKING:
    from bot import AluBot


class Lol(
    LolFPC,
    # emote=const.Emote.DankLove,
    name="Lol",
):
    """League of Legends."""


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Lol(bot))
