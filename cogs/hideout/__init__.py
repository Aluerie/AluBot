"""
Features thar are probably going to stay
**exclusive** to AluBot hideout server
"""

from emote_spam import EmoteSpam, ComfySpam
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
