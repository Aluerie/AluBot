from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from discord import Embed, File, TextChannel, app_commands, errors, utils, InteractionType
from discord.ext import commands

from utils.var import *

if TYPE_CHECKING:
    from discord import Message
    from utils.bot import AluBot
    from utils.bot import Context


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
        Embed Builder command
        @param ctx:
        @return:
        """
        em = Embed(
            title='Hello'
        )
        await ctx.reply(embed=em)


async def setup(bot):
    await bot.add_cog(EmbedMaker(bot))