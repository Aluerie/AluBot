from __future__ import annotations

from typing import TYPE_CHECKING, override

from utils import const

from .notifications import Notifications
from .settings import Settings
from .summoner_check import SummonerNameCheck
from .twitch_check import TwitchAccountCheck

if TYPE_CHECKING:
    from bot import AluBot


class LolFPC(
    Notifications,
    Settings,
    SummonerNameCheck,
    TwitchAccountCheck,
    emote=const.Emote.PogChampPepe,
    name="League of Legends FPC",  # careful with this name since it's used in `database_management.py`
):
    """LoL - __F__avourite __P__layer+__C__haracter combo notifications.
    """

    @override
    async def cog_load(self) -> None:
        await self.bot.initialize_league_pulsefire_clients()
        await self.bot.initialize_twitch()
        return await super().cog_load()


async def setup(bot: AluBot) -> None:
    await bot.add_cog(LolFPC(bot))
