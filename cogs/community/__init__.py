"""
# Glossary 

Community - it's just a server for Aluerie's small community where the bot resides. 
It functions as both bot support server and community as in Aluerie followers, friends, etc. 
The features in these cogs are probably going to stay exclusive to the community server.
"""

from .emote_spam import ComfySpam, EmoteSpam
from .new_reaction_roles import ColourRoles
from .stats import StatsVoiceChannels
from .stream_name import StreamChannelName

COMMUNITY_COGS = (EmoteSpam, ComfySpam, StatsVoiceChannels, StreamChannelName, ColourRoles)


async def setup(bot):
    for m in COMMUNITY_COGS:
        await bot.add_cog(m(bot))
