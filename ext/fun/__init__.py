from __future__ import annotations

from typing import TYPE_CHECKING

from utils.const import Emote

from .mini_games import MiniGames
from .other import FunOther

if TYPE_CHECKING:
    from bot import AluBot


class Fun(
    FunOther,
    MiniGames,
    emote=Emote.FeelsDankMan,
):
    """Commands to have fun with."""


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Fun(bot))
