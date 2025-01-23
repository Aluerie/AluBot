from __future__ import annotations

import asyncio
import datetime
import platform
from typing import TYPE_CHECKING, override

from discord.ext import commands

from bot import aluloop

from ._base import CommunityCog

if TYPE_CHECKING:
    import discord

    from bot import AluBot


class StatsVoiceChannels(CommunityCog):
    """Keep flavour info as names for private voice channels.

    To be honest, this is discord API abuse.
    Names for discord channels are not supposed to used like this.
    This is why the tasks for this should be extremely carefully spaced between each other.
    """

    @override
    async def cog_load(self) -> None:
        self.my_time.start()

        self._lock: asyncio.Lock = asyncio.Lock()
        self.cooldown: datetime.timedelta = datetime.timedelta(seconds=3600)
        self._most_recent: datetime.datetime | None = None

    @override
    async def cog_unload(self) -> None:
        self.my_time.stop()

    @aluloop(time=[datetime.time(hour=x) for x in range(24)])  # 24 times a day
    async def my_time(self) -> None:
        """Update channel name to show Irene's Current Time."""
        symbol = "#" if platform.system() == "Windows" else "-"
        msk_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
        new_name = f'\N{ALARM CLOCK} {msk_now.strftime(f"%{symbol}I %p")}, MSK, Aluerie time'
        await self.bot.community.my_time.edit(name=new_name)

    @commands.Cog.listener("on_member_join")
    @commands.Cog.listener("on_member_remove")
    async def refresh_member_stats(self, member: discord.Member) -> None:
        """Update channel name to show Total People/Bots numbers in the community."""
        async with self._lock:
            if self._most_recent and (delta := datetime.datetime.now(datetime.UTC) - self._most_recent) < self.cooldown:
                # We have to wait
                total_seconds = delta.total_seconds()
                await asyncio.sleep(total_seconds)

            self._most_recent = datetime.datetime.now(datetime.UTC)

            # Actually edit the channel name;

            # TODO: this is bad because we aren't clearing previous new member states;
            amount_of_bots = len(self.bot.community.bots_role.members)
            # TODO: if it's 0 we should just return or post pone
            amount_of_people = (self.bot.community.guild.member_count or 0) - amount_of_bots

            if member.bot:
                # total bots
                await self.bot.community.total_bots.edit(name=f"\N{ROBOT FACE} Bots: {amount_of_bots}")
            else:
                # total people
                await self.bot.community.total_people.edit(name=f"\N{HOUSE WITH GARDEN} People: {amount_of_people}")


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(StatsVoiceChannels(bot))
