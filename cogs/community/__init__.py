"""
# Glossary 

Community - it's just a server for Aluerie's small community where the bot resides. 
It functions as both bot support server and community as in Aluerie followers, friends, etc. 
The features in these cogs are probably going to stay exclusive to the community server.
"""

from .colour_roles import ColourRoles
from .confessions import Confession
from .emote_spam import ComfySpam, EmoteSpam
from .stats import StatsVoiceChannels
from .stream_name import StreamChannelName
from .suggestions import Suggestions

COMMUNITY_COGS = (EmoteSpam, ComfySpam, StatsVoiceChannels, StreamChannelName, ColourRoles, Suggestions, Confession)


async def setup(bot):
    for m in COMMUNITY_COGS:
        await bot.add_cog(m(bot))
