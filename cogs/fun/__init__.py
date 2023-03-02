import discord

from utils.var import Ems

from .rock_paper_scissors import RockPaperScissorsCommand
from .other import Other


class Fun(
    RockPaperScissorsCommand,
    Other
):
    """
    Commands to have fun with
    """

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(Ems.FeelsDankMan)


async def setup(bot):
    await bot.add_cog(Fun(bot))
