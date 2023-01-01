from __future__ import annotations

import time
import asyncio
import logging
from typing import TYPE_CHECKING, List

import discord
from discord import Embed, app_commands, Interaction, Member
from discord.ext import commands, tasks

from .dota.const import ODOTA_API_URL
from .utils.var import *

from .utils.context import Context

if TYPE_CHECKING:
    from .utils.bot import AluBot
    from main import DRecord

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

from discord.app_commands import AppCommandError, Transform, Transformer, Choice, command
from discord import app_commands, Interaction


class UserRecord(DRecord):
    id: int
    name: str


class BetaTest(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
        self.test_task.start()

    @tasks.loop(seconds=20)
    async def test_task(self):
        query = 'SELECT id, name FROM users WHERE id=$1'
        record: UserRecord = await self.bot.pool.fetchrow(query, Uid.alu)
        print(record)

        return

    @app_commands.command()
    async def welp(self, ntr: Interaction):
        await ntr.followup.send('allo')

    @commands.hybrid_command()
    async def allu(self, ctx: Context, member: Member):
        raise ValueError

    @test_task.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    if bot.test:
        await bot.add_cog(BetaTest(bot))
