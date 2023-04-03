"""
# Glossary 

Community - it's just a server for Aluerie's small community where the bot resides. 
It functions as both bot support server and community as in Aluerie followers, friends, etc. 
The features in these cogs are probably going to stay exclusive to the community server.
"""

from .emote_spam import ComfySpam, EmoteSpam
from .stats import StatsVoiceChannels
from .stream_name import StreamChannelName

HIDEOUT_COGS = (
    EmoteSpam,
    ComfySpam,
    StatsVoiceChannels,
    StreamChannelName,
)


async def setup(bot):
    for m in HIDEOUT_COGS:
        await bot.add_cog(m(bot))
