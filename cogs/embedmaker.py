"""
The interactive embed maker command with buttons and modals !

Honestly, some ideas and concepts are looked up from @imptype's messagermaker.py gist:
https://gist.github.com/imptype/7b35c6769684fb68178e5719e5f81b6d
Of course, code below is not a copypaste, but credit must be still given.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from discord import (
    Embed,
    ButtonStyle
)
from discord.ext import commands
from discord.ui import View, button

from .utils.var import Ems, Clr

if TYPE_CHECKING:
    from discord import Message, Interaction
    from discord.ui import Button
    from .utils.bot import AluBot, Context


class StartView(View):
    def __init__(
            self,
            *,
            message: Optional[Message] = None,
    ):
        super().__init__()

        self.starting_embed = Embed(
            colour=Clr.prpl,
            title='Embed Maker'
        )

        self.embeds = [self.starting_embed]
        self.message = message

    @button(label='Author', emoji='🖋️', style=ButtonStyle.blurple)
    async def author_btn(self, ntr: Interaction, btn: Button):

        return 1


class EmbedMaker(commands.Cog, name='Embed Maker'):
    def __init__(self, bot):
        self.bot: AluBot = bot
        self.help_emote = Ems.DankZzz

    @commands.hybrid_group(name='embed')
    async def embed_(self, ctx: Context):
        """Group command about Embed Build, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @embed_.command()
    async def make(self, ctx: Context):
        """
        Embed Maker command. Opens a menu for making/editing/importing embed messages.
        """
        view = StartView()
        view.message = await ctx.reply(embeds=view.embeds, view=view)


async def setup(bot):
    await bot.add_cog(EmbedMaker(bot))
