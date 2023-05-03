import discord

from utils.const import Emote

from .dev_utils import DevUtilities


class Utilities(
    DevUtilities,
):
    """
    Utilities
    """

    @property
    def help_emote(self) -> discord.PartialEmoji:
        # todo: different emote - this one is taken
        return discord.PartialEmoji.from_str(Emote.FeelsDankManLostHisHat)


async def setup(bot):
    await bot.add_cog(Utilities(bot))
