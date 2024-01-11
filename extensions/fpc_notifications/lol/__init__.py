from utils import const

from .notifications import LoLFPCNotifications
from .settings import LoLFPCSettings
from .summoner_check import LoLSummonerNameCheck
from .twitch_check import LoLTwitchAccountCheck


class LoLFPC(
    LoLFPCNotifications,
    LoLFPCSettings,
    LoLSummonerNameCheck,
    LoLTwitchAccountCheck,
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
