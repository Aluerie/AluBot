"""
These cogs are about my private one-person server
and provide features for only me
"""

from .channel_watcher import EventPassWatcher
from .personal import PersonalCommands
from .scrab import Insider, LoLCom

PERSONAL_COGS = (
    EventPassWatcher,
    PersonalCommands,
    Insider,
    LoLCom
)


async def setup(bot):
    for C in PERSONAL_COGS:
        await bot.add_cog(C(bot))
