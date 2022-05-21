from __future__ import annotations
from typing import TYPE_CHECKING, Annotated

from discord import Embed, app_commands
from discord.ext import commands

from utils.var import *
from utils import time

import asyncio

if TYPE_CHECKING:
    from utils.context import Context


class BetaTest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group()
    async def remind(self, ctx):
        await ctx.reply('remind group')

    @remind.command(name='add')
    async def add_ext(self, ctx: Context):
        await ctx.reply('text add')


async def setup(bot):
    if bot.yen:
        await bot.add_cog(BetaTest(bot))
