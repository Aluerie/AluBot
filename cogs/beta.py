from __future__ import annotations

from typing import TYPE_CHECKING

from discord import Embed
from discord.ext import commands

from .utils.database import Tags

if TYPE_CHECKING:
    from .utils.bot import AluBot, Context


class BetaTest(commands.Cog):
    def __init__(self, bot):
        self.bot: AluBot = bot

    def cog_unload(self):
        return

    @commands.hybrid_command()
    async def allu(self, ctx: Context):

        async def create_user():
            await Tags.create(
                name="krappium",
                owner_id=ctx.author.id,
                content='Krapp, Krappa, Krappa, Krappa xd xd xd',
            )

        await create_user()
        user = await Tags.get(1)
        em = Embed(
            description=f'allu {user.id} {user.content}'
        )
        await ctx.reply(embed=em)


async def setup(bot):
    if bot.yen:
        await bot.add_cog(BetaTest(bot))
