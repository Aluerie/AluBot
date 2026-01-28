from __future__ import annotations

from typing import TYPE_CHECKING, override

from utils import const

from .notifications import Notifications
from .settings import LolFPCSettings
from .summoner_check import SummonerNameCheck

if TYPE_CHECKING:
    from bot import AluBot

__all__ = ("LolFPC",)


class LolFPC(
    Notifications,
    LolFPCSettings,
    SummonerNameCheck,
    # emote=const.Emote.PogChampPepe,
    name="League of Legends FPC",  # careful with this name since it's used in `database_management.py`
):
    """League of Legends - __F__avourite __P__layer+__C__haracter combo notifications."""

    @override
    async def cog_load(self) -> None:
        self.bot.instantiate_lol()
        await self.bot.lol.start()
        await self.bot.instantiate_twitch()
        return await super().cog_load()


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(LolFPC(bot))
