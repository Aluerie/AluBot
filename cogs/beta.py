from __future__ import annotations
from typing import TYPE_CHECKING

from dateparser.search import search_dates
from discord import Embed, app_commands, Role, Member, Colour, Interaction, NotFound
from discord.ext import commands

from utils.distools import send_traceback
from utils.format import display_time
from utils.var import *
from utils import time
from utils import database as db

if TYPE_CHECKING:
    from utils.context import Context, Message


class BetaTest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(hidden=True)
    async def allu(self, ctx: Context):
        await ctx.reply('Allu')


async def setup(bot):
    if bot.yen:
        await bot.add_cog(BetaTest(bot))
