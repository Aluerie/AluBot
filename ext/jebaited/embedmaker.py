"""
The interactive embed maker command with buttons and modals !

Honestly, some ideas and concepts are looked up from @imptype's messagermaker.py gist:
https://gist.github.com/imptype/7b35c6769684fb68178e5719e5f81b6d
Of course, code below is not a copypaste, but credit must be still given.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands

from utils import AluCog, const

from ._base import JebaitedCog

if TYPE_CHECKING:
    from utils import AluContext


class StartView(discord.ui.View):
    def __init__(
        self,
        *,
        message: Optional[discord.Message] = None,
    ):
        super().__init__()

        self.starting_embed = discord.Embed(title='Embed Maker', colour=const.Colour.prpl())
        self.embeds = [self.starting_embed]
        self.message = message

    @discord.ui.button(label='Author', emoji='\N{LOWER LEFT FOUNTAIN PEN}', style=discord.ButtonStyle.blurple)
    async def author_button(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await interaction.response.send_message("hello")


class EmbedMaker(JebaitedCog, name="Embed Maker", emote=const.Emote.DankZzz):
    @commands.hybrid_group(name="embed")
    async def embed_(self, ctx: AluContext):
        """Command about Embed Builder."""
        await ctx.send_help(ctx.command)

    @embed_.command()
    async def make(self, ctx: AluContext):
        """Embed Maker command. Opens a menu for making/editing/importing embed messages."""
        view = StartView()
        view.message = await ctx.reply(embeds=view.embeds, view=view)


async def setup(bot):
    await bot.add_cog(EmbedMaker(bot))
