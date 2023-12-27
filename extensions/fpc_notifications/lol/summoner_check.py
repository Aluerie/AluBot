from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, NamedTuple

from pulsefire.clients import RiotAPIClient

import config
from utils import aluloop

from .._base import FPCCog

if TYPE_CHECKING:

    class AccountRow(NamedTuple):
        id: str
        platform: str
        account_name: str


class LoLSummonerNameCheck(FPCCog):
    async def cog_load(self) -> None:
        self.check_summoner_renames.start()
        return await super().cog_load()

    @aluloop(time=datetime.time(hour=12, minute=11, tzinfo=datetime.timezone.utc))
    async def check_summoner_renames(self):
        if datetime.datetime.now(datetime.timezone.utc).day != 17:
            return

        query = "SELECT id, platform, account_name FROM lol_accounts"
        rows: list[AccountRow] = await self.bot.pool.fetch(query)

        for row in rows:
            async with RiotAPIClient(default_headers={"X-Riot-Token": config.RIOT_API_KEY}) as riot_api_client:
                player = await riot_api_client.get_lol_summoner_v4_by_name(
                    name=row.account_name,
                    region=row.platform,
                )

            if player["name"] != row.account_name:
                query = "UPDATE lol_accounts SET account_name=$1 WHERE id=$2"
                await self.bot.pool.execute(query, player["name"], row.id)
