from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, TypedDict

from utils import aluloop

from . import FPCCog

if TYPE_CHECKING:
    from bot import AluBot

    class CheckAccRenamesQueryRow(TypedDict):
        player_id: int
        twitch_id: int
        display_name: str


__all__ = ("TwitchAccountCheckBase",)


class TwitchAccountCheckBase(FPCCog):
    def __init__(self, bot: AluBot, table_name: str, day: int, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.table_name: str = table_name
        self.day: int = day
        # self.__cog_name__ = f'TwitchAccCheckCog for {table_name}'
        self.check_acc_renames.start()

    @aluloop(time=datetime.time(hour=12, minute=11, tzinfo=datetime.timezone.utc))
    async def check_acc_renames(self):
        if datetime.datetime.now(datetime.timezone.utc).day != self.day:
            return

        query = f"SELECT player_id, twitch_id, display_name FROM {self.table_name} WHERE twitch_id IS NOT NULL"
        rows: list[CheckAccRenamesQueryRow] = await self.bot.pool.fetch(query)

        for row in rows:
            display_name = await self.bot.twitch.name_by_twitch_id(row["twitch_id"])
            if display_name != row["display_name"]:
                query = f"UPDATE {self.table_name} SET display_name=$1 WHERE player_id=$3"
                await self.bot.pool.execute(query, display_name, row["player_id"])
