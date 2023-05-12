from utils import const

from .utilities import EmoteUtilitiesCog


class Emotes(EmoteUtilitiesCog, emote=const.Emote.peepoHappyDank):
    """Commands to moderate servers with"""
    ...


async def setup(bot):
    await bot.add_cog(Emotes(bot))