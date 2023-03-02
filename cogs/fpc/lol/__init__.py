from .notifs import LoLNotifs
from .postmatch import LoLFeedPostMatchEdit
from .settings import LoLFeedToolsCog
from .summoner_check import LoLAccCheck
from .twitch_check import LoLTwitchAccountCheck


async def setup(bot):
    await bot.add_cog(LoLNotifs(bot))
    await bot.add_cog(LoLFeedPostMatchEdit(bot))
    await bot.add_cog(LoLFeedToolsCog(bot))
    await bot.add_cog(LoLAccCheck(bot))
    await bot.add_cog(LoLTwitchAccountCheck(bot))
