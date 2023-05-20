from .notifs import LoLNotifs
from .postmatch import LoLFeedPostMatchEdit
from .settings import LoLNotifsSettings
from .summoner_check import LoLSummonerNameCheck
from .twitch_check import LoLTwitchAccountCheck

from utils import const

class LoLFPC(
    LoLNotifs,
    LoLFeedPostMatchEdit,
    LoLNotifsSettings,
    LoLSummonerNameCheck,
    LoLTwitchAccountCheck,
    emote=const.Emote.PogChampPepe
):
    """
    LoL - Favourite player+character combo notifications.
    """


async def setup(bot):
    await bot.add_cog(LoLFPC(bot))
