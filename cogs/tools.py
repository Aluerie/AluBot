from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image

from utils import AluCog, const
from utils.translator import translate

if TYPE_CHECKING:
    from utils import AluBot, AluContext


class ToolsCog(AluCog, name='Tools', emote=const.Emote.DankFix):
    """Some useful stuff

    Maybe one day it's going to be helpful for somebody.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.translate_ctx_menu = app_commands.ContextMenu(
            name='Translate to English', callback=self.translate_ctx_menu_callback
        )

    def cog_load(self) -> None:
        self.bot.ini_twitter()
        self.bot.tree.add_command(self.translate_ctx_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.translate_ctx_menu.name, type=self.translate_ctx_menu.type)

    async def translate_embed(self, text: str):
        # TranslateError is handled in global ErrorHandler, maybe we need to rework it tho
        # into try/except or cog_error
        result = await translate(text, session=self.bot.session)

        e = discord.Embed(title='Google Translate to English', colour=const.Colour.prpl())
        e.description = result.translated
        e.set_footer(text=f'Detected language: {result.source_lang}')
        return e

    async def translate_ctx_menu_callback(self, ntr: discord.Interaction, message: discord.Message):
        if len(text := message.content) == 0:
            raise commands.BadArgument("Sorry it seEmote this message doesn't have content")
        e = await self.translate_embed(text)
        await ntr.response.send_message(embed=e, ephemeral=True)

    @commands.hybrid_command()
    @app_commands.describe(text="Enter text to translate")
    async def translate(self, ctx: AluContext, text: str):
        """Google Translate to English, auto-detects source language"""
        e = await self.translate_embed(text)
        await ctx.reply(embed=e)

    @commands.hybrid_command()
    @app_commands.describe(url='Url of image to convert')
    async def convert(self, ctx: AluContext, *, url: str):
        """Convert image from webp to png format"""
        img = await self.bot.imgtools.url_to_img(url)
        maxsize = (112, 112)  # TODO: remake this function to have all possible fun flags
        img.thumbnail(maxsize, Image.ANTIALIAS)
        file = self.bot.imgtools.img_to_file(img, filename='converted.png', fmt='PNG')
        e = discord.Embed(colour=const.Colour.prpl(), description='Image was converted to `.png` format')
        await ctx.reply(embed=e, file=file)


async def setup(bot: AluBot):
    await bot.add_cog(ToolsCog(bot))
