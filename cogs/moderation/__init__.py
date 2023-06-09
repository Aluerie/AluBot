from utils import const

from .tools import ModerationTools


class Moderation(ModerationTools, emote=const.Emote.peepoPolice):
    """Commands to moderate servers with. 
    
    Discord standard features offer a lot of tools for moderation, 
    however I can offer some extra tools.
    """


async def setup(bot):
    await bot.add_cog(Moderation(bot))
