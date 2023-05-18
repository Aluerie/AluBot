from .notifs import LoLNotifs
from .postmatch import LoLFeedPostMatchEdit
from .settings import LoLNotifsSettings
from .summoner_check import LoLSummonerNameCheck
from .twitch_check import LoLTwitchAccountCheck


class LoL2FPC(
    LoLNotifs,
    LoLFeedPostMatchEdit,
    LoLNotifsSettings,
    LoLSummonerNameCheck,
    LoLTwitchAccountCheck,
):
    """
    LoL - Favourite player+character combo notifications.
    """


async def setup(bot):
    await bot.add_cog(LoL2FPC(bot))
