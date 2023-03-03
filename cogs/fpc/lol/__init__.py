from .notifs import LoLNotifs
from .postmatch import LoLFeedPostMatchEdit
from .settings import LoLNotifsSettings
from .summoner_check import LoLSummonerNameCheck
from .twitch_check import LoLTwitchAccountCheck

LOL_COGS = (
    LoLNotifs,
    LoLFeedPostMatchEdit,
    LoLNotifsSettings,
    LoLSummonerNameCheck,
    LoLTwitchAccountCheck,
)


async def setup(bot):
    for C in LOL_COGS:
        await bot.add_cog(C(bot))
