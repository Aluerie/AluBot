from utils import const

from .utilities import ModUtilitiesCog


class Moderation(ModUtilitiesCog, emote=const.Emote.peepoPolice):
    """Commands to moderate servers with"""
    ...


async def setup(bot):
    await bot.add_cog(Moderation(bot))