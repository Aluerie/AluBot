from __future__ import annotations
from typing import TYPE_CHECKING

import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .utils.context import Context
from .utils.var import Cid

if TYPE_CHECKING:
    from .utils.bot import AluBot

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class BetaTest(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
        self.test_task.start()

    @tasks.loop(count=1)
    async def test_task(self):
        content = '\N{UPWARDS BLACK ARROW}'
        await self.bot.get_channel(Cid.spam_me).send(content)
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
