from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw

from dateparser.search import search_dates
from discord import Embed, Message, app_commands, Role, Member, Colour, Interaction, NotFound, File
from discord.ext import commands

from cogs.expsys import avatar_work
from utils.distools import send_traceback
from utils.format import display_time
from utils.imgtools import url_to_img, img_to_file
from utils.var import *
from utils import time
from utils import database as db

if TYPE_CHECKING:
    from utils.context import Context


class BetaTest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    async def allu(self, ctx: Context):
        await ctx.send('Allu')


async def setup(bot):
    if bot.yen:
        await bot.add_cog(BetaTest(bot))
