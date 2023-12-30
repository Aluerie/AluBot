from utils import const

from .._base import FPCCog
from .notifications import LoLFPCNotifications
from .settings import LoLNotifsSettings
from .summoner_check import LoLSummonerNameCheck
from .twitch_check import LoLTwitchAccountCheck


class LoLFPC(
    LoLFPCNotifications,
    LoLNotifsSettings,
    LoLSummonerNameCheck,
    LoLTwitchAccountCheck,
    FPCCog,
    emote=const.Emote.PogChampPepe,
):
    """
    LoL - Favourite player+character combo notifications.
    """

    async def cog_load(self) -> None:
        await self.bot.initiate_twitch()
        return await super().cog_load()


async def setup(bot):
    await bot.add_cog(LoLFPC(bot))
