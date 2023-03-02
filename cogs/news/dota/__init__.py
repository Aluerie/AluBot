from .bugtracker import BugTracker
from .dota2com import Dota2Com
from .reddit import Reddit
from .steamdb import SteamDB
from .twitter import Twitter


async def setup(bot):
    await bot.add_cog(BugTracker(bot))
    await bot.add_cog(Dota2Com(bot))
    await bot.add_cog(Reddit(bot))
    await bot.add_cog(SteamDB(bot))
    await bot.add_cog(Twitter(bot))
