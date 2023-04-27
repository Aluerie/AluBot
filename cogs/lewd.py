from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

from utils import AluCog, Ems

if TYPE_CHECKING:
    from utils import AluBot, AluContext


class LewdCog(AluCog, name='Lewd', emote=Ems.peepoPlsStepOnMe):
    """NSFW tier commands

    Horny, huh
    """

    @commands.hybrid_command()
    async def lewd(self, ctx: AluContext):
        """[NSFW] Get a random horny picture."""
        await ctx.reply('Coming soon {0} {0} {0}'.format(Ems.Jebaited))


async def setup(bot: AluBot):
    await bot.add_cog(LewdCog(bot))
