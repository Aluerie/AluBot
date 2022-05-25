from __future__ import annotations
from typing import TYPE_CHECKING

from discord import app_commands
from discord.ext import commands

from utils.var import *

if TYPE_CHECKING:
    from utils.context import Context


class LewdCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_category = 'Lewd'

    @commands.hybrid_command()
    async def lewd(self, ctx: Context):
        await ctx.reply(f'Coming soon {Ems.Jebaited}')


async def setup(bot):
    await bot.add_cog(LewdCog(bot))
