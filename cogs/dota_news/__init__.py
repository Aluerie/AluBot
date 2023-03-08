from .bugtracker import BugTracker
from .dota2com import Dota2Com
from .reddit import Reddit
from .steamdb import SteamDB
from .twitter import Twitter

DOTA_NEWS_COGS = (
    BugTracker,
    Dota2Com,
    Reddit,
    SteamDB,
    Twitter
)

async def setup(bot):
    for C in DOTA_NEWS_COGS:
        await bot.add_cog(C(bot))

