from __future__ import annotations
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from utils.var import Ems

if TYPE_CHECKING:
    from utils.bot import AluBot
    from utils.context import Context


class LewdCog(commands.Cog, name='Lewd'):
    """NSFW tier commands

    Horny, huh
    """

    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(Ems.peepoPlsStepOnMe)

    @commands.hybrid_command()
    async def lewd(self, ctx: Context):
        """[NSFW] Get a random horny picture."""
        await ctx.reply('Coming soon {0} {0} {0}'.format(Ems.Jebaited))


async def setup(bot: AluBot):
    await bot.add_cog(LewdCog(bot))
