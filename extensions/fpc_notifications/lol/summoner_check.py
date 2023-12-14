from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from utils import aluloop

from .._base import FPCCog

if TYPE_CHECKING:
    pass


class LoLSummonerNameCheck(FPCCog):
    async def cog_load(self) -> None:
        self.check_summoner_renames.start()
        return await super().cog_load()

    @aluloop(time=datetime.time(hour=12, minute=11, tzinfo=datetime.timezone.utc))
    async def check_summoner_renames(self):
        if datetime.datetime.now(datetime.timezone.utc).day != 17:
            return

        query = "SELECT id, platform, account_name FROM lol_accounts"
        rows = await self.bot.pool.fetch(query)

        for row in rows:
            async with self.bot.riot_api_client as riot_api_client:
                player = await riot_api_client.get_lol_summoner_v4_by_name(name=row.account, region=row.platform)

            if player["name"] != row.account:
                query = "UPDATE lol_accounts SET account_name=$1 WHERE id=$2"
                await self.bot.pool.execute(query, player["name"], row.id)
