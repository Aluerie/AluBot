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

from .utils.var import Ems, Clr

if TYPE_CHECKING:
    from .utils.bot import AluBot
    from .utils.context import Context


class StartView(discord.ui.View):
    def __init__(
            self,
            *,
            message: Optional[discord.Message] = None,
    ):
        super().__init__()

        self.starting_embed = discord.Embed(title='Embed Maker', colour=Clr.prpl)
        self.embeds = [self.starting_embed]
        self.message = message

    @discord.ui.button(label='Author', emoji='🖋️', style=discord.ButtonStyle.blurple)
    async def author_btn(self, ntr: discord.Interaction, btn: discord.Button):

        return 1


class EmbedMaker(commands.Cog, name='Embed Maker'):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(Ems.DankZzz)

    @commands.hybrid_group(name='embed')
    async def embed_(self, ctx: Context):
        """Group command about Embed Build, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @embed_.command()
    async def make(self, ctx: Context):
        """Embed Maker command. Opens a menu for making/editing/importing embed messages."""
        view = StartView()
        view.message = await ctx.reply(embeds=view.embeds, view=view)


async def setup(bot: AluBot):
    await bot.add_cog(EmbedMaker(bot))
