from __future__ import annotations
from typing import TYPE_CHECKING

import asyncio

import discord
from discord.ext import commands, tasks

from .utils.var import Uid

if TYPE_CHECKING:
    from .utils.bot import AluBot

start_errors = 948936198733328425
game_feed = 966316773869772860


class PassEvent(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    async def cog_load(self) -> None:
        pass

    async def cog_unload(self) -> None:
        self.botcheck.cancel()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.id == game_feed:
            self.botcheck.restart()

    @tasks.loop()
    async def botcheck(self):
        await asyncio.sleep(52 * 60)  # let's assume the longest possible game+q time is ~52 mins
        channel: discord.TextChannel = self.bot.get_channel(start_errors)  # type: ignore
        await channel.send(  f'<@{Uid.alu}> I think the bot crashed but did not even send the message')

    @botcheck.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot: AluBot):
    await bot.add_cog(PassEvent(bot))
