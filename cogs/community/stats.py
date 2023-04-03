from __future__ import annotations
from typing import TYPE_CHECKING

import datetime
import platform

import discord
from discord.ext import tasks

from utils.var import Rid

from ._base import HideoutBase

if TYPE_CHECKING:
    pass

# Voice Channels which titles will show various stats
# todo: these ids to wiki
MY_TIME_CHANNEL = 788915790543323156
TOTAL_MEMBERS_CHANNEL = 795743012789551104
TOTAL_BOTS_CHANNEL = 795743065787990066


class StatsVoiceChannels(HideoutBase):
    async def cog_load(self) -> None:
        self.my_time.start()
        self.total_members.start()
        self.total_bots.start()

    async def cog_unload(self) -> None:
        self.my_time.stop()
        self.total_members.stop()
        self.total_bots.stop()

    @tasks.loop(time=[datetime.time(hour=x) for x in range(0, 24)])
    async def my_time(self):
        symbol = '#' if platform.system() == 'Windows' else '-'
        msk_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
        new_name = f'\N{ALARM CLOCK} {msk_now.strftime(f"%{symbol}I %p")}, MSK, Aluerie time'
        await self.bot.get_channel(MY_TIME_CHANNEL).edit(name=new_name)

    @my_time.before_loop
    async def my_time_before(self):
        await self.bot.wait_until_ready()

    @property
    def bots_role(self) -> discord.Role:
        return self.community.get_role(Rid.bots)  # type: ignore 

    @tasks.loop(time=[datetime.time(hour=3)])
    async def total_members(self):
        guild = self.community
        bots_role = self.bots_role
        channel: discord.VoiceChannel = guild.get_channel(TOTAL_MEMBERS_CHANNEL)  # type: ignore # known ID
        member_count = guild.member_count or 0
        new_name = f'\N{HOUSE WITH GARDEN} Members: {member_count - len(bots_role.members)}'
        await channel.edit(name=new_name)

    @total_members.before_loop
    async def total_members_before(self):
        await self.bot.wait_until_ready()

    @tasks.loop(time=[datetime.time(hour=3)])
    async def total_bots(self):
        guild = self.community
        bots_role = self.bots_role
        channel: discord.VoiceChannel = guild.get_channel(TOTAL_BOTS_CHANNEL)  # type: ignore # known ID
        new_name = f'\N{ROBOT FACE} Bots: {len(bots_role.members)}'
        await channel.edit(name=new_name)

    @total_bots.before_loop
    async def total_bots_before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(StatsVoiceChannels(bot))
