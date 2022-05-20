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

    @commands.hybrid_command()
    @app_commands.default_permissions(manage_messages=True)
    async def allo(
            self,
            ctx: Context,
            *,
            dt_str: Annotated[time.FriendlyTimeResult, time.UserFriendlyTime(commands.clean_content, default='…')]
    ):
        print(dt_str.dt, dt_str.arg)
        await ctx.reply('allo')


async def setup(bot):
    if bot.yen:
        await bot.add_cog(BetaTest(bot))
