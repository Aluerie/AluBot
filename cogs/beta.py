from __future__ import annotations
from typing import TYPE_CHECKING

from discord.ext import commands

from utils.var import *

import asyncio

if TYPE_CHECKING:
    from utils.context import Context


class BetaTest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.is_owner()
    @commands.hybrid_command()
    async def allo(self, ctx: Context):
        await ctx.reply(Ems.bubuAyaya)


async def setup(bot):
    if bot.yen:
        await bot.add_cog(BetaTest(bot))
