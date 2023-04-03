"""
# Glossary

"hideout" - my private one-person discord server where I hide out: 
test the bot, have logs from the bot and other projects, save any kinds of info, have news-RSS channels, etc. 

So these features are intended to be used only by me and only in my hideout server.
"""

from .channel_watcher import EventPassWatcher
from .personal import PersonalCommands
from .scrape import Insider, LoLCom

PERSONAL_COGS = (
    EventPassWatcher,
    PersonalCommands,
    Insider,
    LoLCom
)


async def setup(bot):
    for C in PERSONAL_COGS:
        await bot.add_cog(C(bot))
