from .notifs import LoLNotifs
from .postmatch import LoLFeedPostMatchEdit
from .settings import LoLNotifsSettings
from .summoner_check import LoLSummonerNameCheck
from .twitch_check import LoLTwitchAccountCheck


async def setup(bot):
    await bot.add_cog(LoLNotifs(bot))
    await bot.add_cog(LoLFeedPostMatchEdit(bot))
    await bot.add_cog(LoLNotifsSettings(bot))
    await bot.add_cog(LoLSummonerNameCheck(bot))
    await bot.add_cog(LoLTwitchAccountCheck(bot))
