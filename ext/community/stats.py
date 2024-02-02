from __future__ import annotations

import datetime
import platform
from typing import TYPE_CHECKING, override

from utils import aluloop

from ._base import CommunityCog

if TYPE_CHECKING:
    from bot import AluBot


class StatsVoiceChannels(CommunityCog):
    @override
    async def cog_load(self) -> None:
        self.my_time.start()
        self.refresh_member_stats.start()

    @override
    async def cog_unload(self) -> None:
        self.my_time.stop()
        self.refresh_member_stats.stop()

    @aluloop(time=[datetime.time(hour=x) for x in range(0, 24)])  # 24 times a day
    async def my_time(self) -> None:
        symbol = "#" if platform.system() == "Windows" else "-"
        msk_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
        new_name = f'\N{ALARM CLOCK} {msk_now.strftime(f"%{symbol}I %p")}, MSK, Aluerie time'
        await self.bot.community.my_time.edit(name=new_name)

    @aluloop(time=[datetime.time(hour=3)])  # once a day
    async def refresh_member_stats(self) -> None:
        amount_of_bots = len(self.bot.community.bots_role.members)
        amount_of_people = (self.bot.community.guild.member_count or 0) - amount_of_bots

        # total people
        await self.bot.community.total_people.edit(name=f"\N{HOUSE WITH GARDEN} People: {amount_of_people}")

        # total bots
        await self.bot.community.total_bots.edit(name=f"\N{ROBOT FACE} Bots: {amount_of_bots}")


async def setup(bot: AluBot) -> None:
    await bot.add_cog(StatsVoiceChannels(bot))
