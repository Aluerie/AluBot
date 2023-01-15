from __future__ import annotations
from typing import TYPE_CHECKING, Optional

import asyncio

import discord
from discord.ext import commands, tasks

from .utils.var import Clr, Uid, Sid

if TYPE_CHECKING:
    from .utils.bot import AluBot

start_errors = 948936198733328425
game_feed = 966316773869772860


class PassEvent(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
        self.pass_live: Optional[bool] = None

    async def cog_load(self) -> None:
        query = 'SELECT event_pass_is_live FROM botinfo WHERE id=$1'
        self.pass_live = p = await self.bot.pool.fetchval(query, Sid.alu)
        if p:
            self.pass_check.start()

    async def cog_unload(self) -> None:
        self.pass_check.cancel()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.id == game_feed:
            if self.pass_check.is_running():
                self.pass_check.restart()
                if not self.pass_live:
                    query = 'UPDATE botinfo SET event_pass_is_live=TRUE WHERE id=$1'
                    await self.bot.pool.execute(query, Sid.alu)
                    self.pass_live = True
            else:
                self.pass_check.start()

    @tasks.loop(count=1)
    async def pass_check(self):
        await asyncio.sleep(50*60)  # let's assume the longest possible game+q time is ~50 mins
        channel: discord.TextChannel = self.bot.get_channel(start_errors)  # type: ignore
        e = discord.Embed(colour=Clr.error)
        e.description = 'The bot crashed but did not even send the message'
        e.set_footer(text='Or maybe event just ended')
        await channel.send(f'<@{Uid.alu}>', embed=e)
        query = 'UPDATE botinfo SET event_pass_is_live=TRUE WHERE id=$1'
        await self.bot.pool.execute(query, Sid.alu)

    @pass_check.error
    async def pass_check_error(self, error):
        await self.bot.send_traceback(error, where='PassEvent check')
        # self.git_comments_check.restart()

    @pass_check.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot: AluBot):
    await bot.add_cog(PassEvent(bot))
