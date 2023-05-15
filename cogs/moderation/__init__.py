from utils import const

from .utilities import ModUtilitiesCog
from .clean import CleanCog


class Moderation(ModUtilitiesCog, CleanCog, emote=const.Emote.peepoPolice):
    """Commands to moderate servers with"""


async def setup(bot):
    await bot.add_cog(Moderation(bot))