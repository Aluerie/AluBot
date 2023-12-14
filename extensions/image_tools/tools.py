from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image

from utils import const

from ._base import ImageToolsCog

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluContext


class ToolsCog(ImageToolsCog, name="Tools", emote=const.Emote.DankFix):
    """Some useful stuff

    Maybe one day it's going to be helpful for somebody.
    """

    @commands.hybrid_command()
    @app_commands.describe(url="Url of image to convert")
    async def convert(self, ctx: AluContext, *, url: str):
        """Convert image from webp to png format"""
        img = await self.bot.transposer.url_to_image(url)
        maxsize = (112, 112)  # TODO: remake this function to have all possible fun flags
        img.thumbnail(maxsize, Image.ANTIALIAS)
        file = self.bot.transposer.image_to_file(img, filename="converted.png", extension="PNG")
        e = discord.Embed(colour=const.Colour.prpl(), description="Image was converted to `.png` format")
        await ctx.reply(embed=e, file=file)


async def setup(bot: AluBot):
    await bot.add_cog(ToolsCog(bot))
