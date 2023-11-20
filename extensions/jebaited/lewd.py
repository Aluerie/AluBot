from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

from utils import const

from ._base import JebaitedCog

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluContext


class LewdCog(JebaitedCog, name="Lewd", emote=const.Emote.peepoStepOnMePls):
    """NSFW tier commands

    Horny, huh
    """

    @commands.hybrid_command()
    async def lewd(self, ctx: AluContext):
        """[NSFW] Get a random horny picture."""
        await ctx.reply("Coming soon {0} {0} {0}".format(const.Emote.Jebaited))


async def setup(bot: AluBot):
    await bot.add_cog(LewdCog(bot))
