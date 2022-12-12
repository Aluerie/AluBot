from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

from .utils.var import Ems

if TYPE_CHECKING:
    from .utils.context import Context
    from .utils.context import AluBot


class LewdCog(commands.Cog, name='Lewd'):
    """
    NSFW tier commands

    Horny, huh
    """

    def __init__(self, bot):
        self.bot: AluBot = bot
        self.help_emote = Ems.peepoPlsStepOnMe

    @commands.hybrid_command()
    async def lewd(self, ctx: Context):
        """
        [NSFW] Get a random horny picture.
        """
        await ctx.reply('Coming soon {0} {0} {0}'.format(Ems.Jebaited))


async def setup(bot):
    await bot.add_cog(LewdCog(bot))
