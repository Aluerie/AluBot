import discord

from utils.var import Ems

from .stats import StatsVoiceChannels


class Hideout(
    StatsVoiceChannels
):
    """
    Special Features for Hideout server.
    """

    @property
    def help_emote(self) -> discord.PartialEmoji:
        # todo: find better emote bcs it belongs to fun
        return discord.PartialEmoji.from_str(Ems.FeelsDankMan)


async def setup(bot):
    await bot.add_cog(Hideout(bot))
