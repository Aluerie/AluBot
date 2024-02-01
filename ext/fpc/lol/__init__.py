from utils import const

from .notifications import LoLNotifications
from .settings import LoLFPCSettings
from .summoner_check import LoLSummonerNameCheck
from .twitch_check import LoLTwitchAccountCheck


class LoLFPC(
    LoLNotifications,
    LoLFPCSettings,
    LoLSummonerNameCheck,
    LoLTwitchAccountCheck,
    emote=const.Emote.PogChampPepe,
    name="League of Legends FPC",  # careful with this name since it's used in `database_management.py`
):
    """
    LoL - __F__avourite __P__layer+__C__haracter combo notifications.
    """

    async def cog_load(self) -> None:
        await self.bot.initialize_league_pulsefire_clients()
        await self.bot.initialize_twitch()
        return await super().cog_load()


async def setup(bot) -> None:
    await bot.add_cog(LoLFPC(bot))
