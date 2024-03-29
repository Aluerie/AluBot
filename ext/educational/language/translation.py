from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

import discord
from discord import app_commands
from discord.ext import commands

from utils import const, errors
from utils.translator import translate

from .._base import EducationalCog

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluContext


class TranslateCog(EducationalCog):
    def __init__(self, bot: AluBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)
        self.translate_context_menu = app_commands.ContextMenu(
            name="Translate to English",
            callback=self.translate_context_menu_callback,
        )

    @override
    def cog_load(self) -> None:
        self.bot.tree.add_command(self.translate_context_menu)

    @override
    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.translate_context_menu.name, type=self.translate_context_menu.type)

    async def translate_embed(self, text: str) -> discord.Embed:
        # PS: TranslateError is handled in global ErrorHandler
        result = await translate(text, session=self.bot.session)

        return discord.Embed(
            colour=const.Colour.blueviolet,
            title="Google Translate to English",
            description=result.translated,
        ).set_footer(text=f"Detected language: {result.source_lang}")

    async def translate_context_menu_callback(self, interaction: discord.Interaction, message: discord.Message) -> None:
        if len(text := message.content) == 0:
            msg = "Sorry, but it seems, that this message doesn't have any text content to translate."
            raise errors.BadArgument(msg)
        e = await self.translate_embed(text)
        await interaction.response.send_message(embed=e, ephemeral=True)

    @commands.hybrid_command()
    @app_commands.describe(text="Enter text to translate")
    async def translate(self, ctx: AluContext, text: str) -> None:
        """Google Translate to English, auto-detects source language."""
        e = await self.translate_embed(text)
        await ctx.reply(embed=e)
