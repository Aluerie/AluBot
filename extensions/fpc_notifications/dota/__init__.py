from utils import const

from .._base import FPCCog
from .notifications import DotaFPCNotifications
from .settings import DotaFPCSettings
from .twitch_check import DotaTwitchAccountCheck


class DotaFPC(
    DotaFPCNotifications,
    DotaFPCSettings,
    DotaTwitchAccountCheck,
    emote=const.Emote.DankLove,
):
    """
    Dota 2 - Favourite player+character combo notifications.
    """

    async def cog_load(self) -> None:
        await self.bot.initiate_steam_dota()
        await self.bot.initiate_twitch()
        return await super().cog_load()


async def setup(bot):
    await bot.add_cog(DotaFPC(bot))
