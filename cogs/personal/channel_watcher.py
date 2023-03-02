from __future__ import annotations
from typing import TYPE_CHECKING

import asyncio

import discord
from discord.ext import commands, tasks

from utils.var import Cid, Clr, Uid, Sid

if TYPE_CHECKING:
    from utils.bot import AluBot


EVENT_PASS_CHANNEL = 966316773869772860
DROPS_CHANNEL = 1074010096566284288


class ChannelWatcher(commands.Cog):
    watch_bool: bool

    def __init__(
        self,
        bot: AluBot,
        db_column: str,
        sleep_time: int,
        watch_channel_id: int,
        ping_channel_id: int,
    ):
        self.bot: AluBot = bot
        self.db_column: str = db_column
        self.sleep_time: int = sleep_time
        self.watch_channel_id: int = watch_channel_id
        self.ping_channel_id: int = ping_channel_id

    async def cog_load(self) -> None:
        query = f'SELECT {self.db_column} FROM botinfo WHERE id=$1'
        self.watch_bool = p = await self.bot.pool.fetchval(query, Sid.alu)
        if p:
            self.sleep_task.start()

    async def cog_unload(self) -> None:
        self.sleep_task.cancel()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.id == self.watch_channel_id:
            if self.sleep_task.is_running():
                self.sleep_task.restart()
                if not self.watch_bool:
                    query = f'UPDATE botinfo SET {self.db_column}=TRUE WHERE id=$1'
                    await self.bot.pool.execute(query, Sid.alu)
                    self.watch_bool = True
            else:
                self.sleep_task.start()

    @tasks.loop(count=1)
    async def sleep_task(self):
        await asyncio.sleep(self.sleep_time)  # let's assume the longest possible game+q time is ~50 mins
        channel: discord.TextChannel = self.bot.get_channel(self.ping_channel_id)  # type: ignore
        e = discord.Embed(colour=Clr.error, title=self.__cog_name__)
        e.description = 'The bot crashed but did not even send the message'
        e.set_footer(text='Or maybe event just ended')
        await channel.send(f'<@{Uid.alu}>', embed=e)
        query = f'UPDATE botinfo SET {self.db_column}=FALSE WHERE id=$1'
        await self.bot.pool.execute(query, Sid.alu)

    @sleep_task.error
    async def pass_check_error(self, error):
        await self.bot.send_traceback(error, where=self.__cog_name__)

    @sleep_task.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


class EventPassWatcher(ChannelWatcher):
    def __init__(self, bot: AluBot):
        super().__init__(
            bot,
            db_column='event_pass_is_live',
            sleep_time=50 * 60,  # 50 minutes
            watch_channel_id=EVENT_PASS_CHANNEL,
            ping_channel_id=Cid.spam_me,
        )


class DropsWatcher(ChannelWatcher):
    def __init__(self, bot: AluBot):
        super().__init__(
            bot,
            db_column='drops_watch_live',
            sleep_time=60 * 60 * 24 * 7,  # a week
            watch_channel_id=1074010096566284288,
            ping_channel_id=Cid.spam_me,
        )


async def setup(bot: AluBot):
    await bot.add_cog(EventPassWatcher(bot))
    await bot.add_cog(DropsWatcher(bot))
