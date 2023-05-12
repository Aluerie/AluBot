from utils import const

from .utilities import EmoteUtilitiesCog


class EmotesCog(EmoteUtilitiesCog, emote=const.Emote.peepoHappyDank):
    """Commands to moderate servers with"""
    pass


async def setup(bot):
    await bot.add_cog(EmotesCog(bot))