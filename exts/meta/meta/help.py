from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Sequence, Union

import discord
from discord import app_commands
from discord.ext import commands

from base.help_cmd import AluHelp
from utils import AluContext, aluloop, const

from .._category import MetaCog

if TYPE_CHECKING:
    from utils import AluBot


class AluHelpCog(MetaCog):
    """Help command."""

    def __init__(self, bot: AluBot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        if bot.help_command:
            bot.help_command.cog = self

    @app_commands.command(name='help')
    @app_commands.describe(query='Command/Section/Category name to get help about.')
    async def slash_help(self, ntr: discord.Interaction, *, query: Optional[str]):
        """Show help menu for the bot."""
        ctx = await AluContext.from_interaction(ntr)
        if query:
            await ctx.send_help(query)
        else:
            await ctx.send_help()
        # todo: starting category
        # my_help = AluHelp()
        # my_help.context = ctx = await AluContext.from_interaction(ntr)
        # await my_help.command_callback(ctx, command=command)

    @commands.is_owner()
    @commands.command(hidden=True)
    async def devhelp(self, ctx: AluContext, *, query: Optional[str]):
        """Show dev help menu for the bot."""
        my_help = AluHelp(show_hidden=True)
        my_help.context = ctx
        await my_help.command_callback(ctx, command=query)


async def setup(bot: AluBot):
    await bot.add_cog(AluHelpCog(bot))
