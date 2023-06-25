"""
Clean state for easier resetting of git-ignored `cogs/beta.py` file where I do various beta testings 
"""
from __future__ import annotations

import asyncio
import datetime
import logging
import os
from typing import TYPE_CHECKING, Annotated, Any, Callable, Coroutine, List, Optional, Sequence, TypeVar, Union

import discord
from discord import app_commands
from discord.ext import commands, menus

from utils import AluCog, aluloop, const, errors

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from utils import AluBot, AluContext


class BetaTestCog(AluCog, name='BetaTest'):
    def __init__(self, bot: AluBot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.beta_task.start()

    @aluloop(count=1)
    async def beta_task(self):
        await self.hideout.spam.send('1')

    @commands.command()
    async def ceta(self, ctx: AluContext):
        await ctx.send('ceta')

    @commands.hybrid_command()
    async def heta(self, ctx: AluContext):
        await ctx.send('heta')

    @app_commands.command()
    async def seta(self, ntr: discord.Interaction):
        await ntr.response.send_message('seta')


async def setup(bot: AluBot):
    await bot.add_cog(BetaTestCog(bot))
