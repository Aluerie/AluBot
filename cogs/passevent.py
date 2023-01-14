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
        self.pass_check.cancel()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.id == game_feed:
            if self.pass_check.is_running():
                self.pass_check.restart()
            else:
                self.pass_check.start()

    @tasks.loop(count=1)
    async def pass_check(self):
        await asyncio.sleep(50*60)  # let's assume the longest possible game+q time is ~50 mins
        channel: discord.TextChannel = self.bot.get_channel(start_errors)  # type: ignore
        await channel.send(  f'<@{Uid.alu}> I think the bot crashed but did not even send the message')

    @pass_check.error
    async def pass_check_error(self, error):
        await self.bot.send_traceback(error, where='PassEvent check')
        # self.git_comments_check.restart()

    @pass_check.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot: AluBot):
    await bot.add_cog(PassEvent(bot))
