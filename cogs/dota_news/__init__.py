from cogs.news.bugtracker import BugTracker
from cogs.news.dota2com import Dota2Com
from cogs.news.reddit import Reddit
from cogs.news.steamdb import SteamDB
from cogs.news.twitter import Twitter


async def setup(bot):
    await bot.add_cog(BugTracker(bot))
    await bot.add_cog(Dota2Com(bot))
    await bot.add_cog(Reddit(bot))
    await bot.add_cog(SteamDB(bot))
    await bot.add_cog(Twitter(bot))
