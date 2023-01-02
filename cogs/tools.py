from __future__ import annotations
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image

from cogs.twitter import download_twitter_images
from .utils.var import Clr, Ems

if TYPE_CHECKING:
    from .utils.bot import AluBot
    from .utils.context import Context


class ToolsCog(commands.Cog, name='Tools'):
    """Some useful stuff

    Maybe one day it's going to be helpful for somebody.
    """

    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
        self.players_by_group = []

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(Ems.DankFix)

    def cog_load(self) -> None:
        self.bot.ini_twitter()

    @commands.hybrid_command(
        name='convert',
        description='Convert image from webp to png format',
    )
    @app_commands.describe(url='Url of image to convert')
    async def convert(self, ctx: Context, *, url: str):
        """Convert image from webp to png format"""
        img = await self.bot.url_to_img(url)
        maxsize = (112, 112)  # TODO: remake this function to have all possible fun flags
        img.thumbnail(maxsize, Image.ANTIALIAS)
        file = self.bot.img_to_file(img, filename='converted.png', fmt='PNG')
        e = discord.Embed(colour=Clr.prpl, description='Image was converted to `.png` format')
        await ctx.reply(embed=e, file=file)

    @commands.hybrid_command()
    @app_commands.describe(tweet_ids='Number(-s) in the end of tweet link')
    async def twitter_image(self, ctx: Context, *, tweet_ids: str):
        """
        Download image from tweets. \
        Useful for Aluerie because Twitter is banned in Russia.
        • `<tweet_ids>` are tweet ids - it's just numbers in the end of tweet links.
        """
        await download_twitter_images(self.bot.session, ctx, tweet_ids=tweet_ids)


async def setup(bot: AluBot):
    # while twitter is banned in russia # TODO: Remove this
    import platform
    if platform.system() == 'Windows':
        return
    await bot.add_cog(ToolsCog(bot))
