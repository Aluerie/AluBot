import discord

from utils.const import Emote

from .dev_utils import DevUtilities
from .embedmaker import EmbedMaker


class Utilities(
    DevUtilities,
    EmbedMaker,
    name='Utilities',
    emote=Emote.FeelsDankManLostHisHat
):
    """
    Utilities
    """


async def setup(bot):
    await bot.add_cog(Utilities(bot))
