from __future__ import annotations
from typing import TYPE_CHECKING

from discord import Embed, app_commands
from discord.ext import commands

from utils.imgtools import url_to_img, img_to_file
from utils.var import *

from PIL import Image

if TYPE_CHECKING:
    from utils.context import Context


class ToolsCog(commands.Cog, name='Tools'):
    """
    Some useful stuff

    Maybe one day it gonna be helpful for somebody.
    """
    def __init__(self, bot):
        self.bot = bot
        self.help_emote = Ems.DankFix

    @commands.hybrid_command(
        name='convert',
        brief=Ems.slash,
        description='Convert image from webp to png format',
    )
    @app_commands.describe(url='Url of image to convert')
    async def convert(self, ctx: Context, *, url: str):
        """Convert image from webp to png format"""
        img = await url_to_img(self.bot.ses, url)
        maxsize = (112, 112)  # TODO: remake this function to have all possible fun flags
        img.thumbnail(maxsize, Image.ANTIALIAS)
        file = img_to_file(img, filename='converted.png', fmt='PNG')
        em = Embed(colour=Clr.prpl, description='Image was converted to png format')
        await ctx.reply(embed=em, file=file)


async def setup(bot):
    await bot.add_cog(ToolsCog(bot))
