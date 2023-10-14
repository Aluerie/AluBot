from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from utils import aluloop, const

from ._base import HideoutCog

if TYPE_CHECKING:
    from utils import AluBot


class ChannelWatcher(HideoutCog):
    def __init__(
        self,
        bot: AluBot,
        db_column: str,
        sleep_time: int,
        watch_channel_id: int,
        ping_channel_id: int,
        role_mention: str = '',
        *args,
        **kwargs,
    ):
        super().__init__(bot, *args, **kwargs)
        self.bot: AluBot = bot
        self.db_column: str = db_column
        self.sleep_time: int = sleep_time
        self.watch_channel_id: int = watch_channel_id
        self.ping_channel_id: int = ping_channel_id
        self.role_mention: str = role_mention
        self.watch_bool: bool = True

    async def cog_load(self) -> None:
        query = f'SELECT {self.db_column} FROM botinfo WHERE id=$1'
        self.watch_bool = p = await self.bot.pool.fetchval(query, const.Guild.community)
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
                    await self.bot.pool.execute(query, const.Guild.community)
                    self.watch_bool = True
            else:
                self.sleep_task.start()

    @aluloop(count=1)
    async def sleep_task(self):
        await asyncio.sleep(self.sleep_time)  # let's assume the longest possible game+q time is ~50 mins
        channel: discord.TextChannel = self.bot.get_channel(self.ping_channel_id)  # type: ignore
        e = discord.Embed(colour=const.Colour.error(), title=self.__cog_name__)
        e.description = 'The bot crashed but did not even send the message'
        e.set_footer(text='Or maybe event just ended')
        await channel.send(self.role_mention, embed=e)
        query = f'UPDATE botinfo SET {self.db_column}=FALSE WHERE id=$1'
        await self.bot.pool.execute(query, const.Guild.community)


class EventPassWatcher(ChannelWatcher):
    def __init__(self, bot: AluBot):
        super().__init__(
            bot,
            db_column='event_pass_is_live',
            sleep_time=60 * 60,  # 60 minutes
            watch_channel_id=const.Channel.event_pass,
            ping_channel_id=const.Channel.spam_me,
            role_mention=const.Role.event.mention,
        )


# looks like the era is over
#
# DROPS_CHANNEL = 1074010096566284288
#
# class DropsWatcher(ChannelWatcher):
#     def __init__(self, bot: AluBot):
#         super().__init__(
#             bot,
#             db_column='drops_watch_live',
#             sleep_time=60 * 60 * 24 * 7,  # a week
#             watch_channel_id=1074010096566284288,
#             ping_channel_id=Channel.spam_me,
#         )


async def setup(bot: AluBot):
    await bot.add_cog(EventPassWatcher(bot))
    # await bot.add_cog(DropsWatcher(bot))
