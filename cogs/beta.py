from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands, tasks
from discord import app_commands

from .utils.var import Uid

from .utils.context import Context
from .utils.database import DRecord

if TYPE_CHECKING:
    from .utils.bot import AluBot

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


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
    async def welp(self, ntr: discord.Interaction):
        await ntr.followup.send('allo')

    @commands.hybrid_command()
    async def allu(self, ctx: Context, member: discord.Member):
        raise ValueError

    @test_task.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    if bot.test:
        await bot.add_cog(BetaTest(bot))
