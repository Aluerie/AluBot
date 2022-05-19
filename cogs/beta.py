from __future__ import annotations
from typing import TYPE_CHECKING

from discord import Embed
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
        images_url = ['https://i.imgur.com/X9v93uk.png',
                      'https://i.imgur.com/X9v93uk.png',
                      'https://i.imgur.com/X9v93uk.png',
                      'https://i.imgur.com/X9v93uk.png']
        embeds = [Embed(url='https://github.com/').set_image(url=url) for url in images_url]
        embeds[0].colour = Clr.prpl
        await ctx.reply(embeds=embeds)


async def setup(bot):
    if bot.yen:
        await bot.add_cog(BetaTest(bot))
