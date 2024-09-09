from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, TypedDict, override

import aiohttp

from bot import aluloop

from ..base_classes import FPCCog

if TYPE_CHECKING:

    class AccountRow(TypedDict):
        puuid: str
        platform: str
        game_name: str
        tag_line: str


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class SummonerNameCheck(FPCCog):
    @override
    async def cog_load(self) -> None:
        self.check_summoner_renames.start()
        return await super().cog_load()

    @aluloop(time=datetime.time(hour=12, minute=11, tzinfo=datetime.UTC))
    async def check_summoner_renames(self) -> None:
        if datetime.datetime.now(datetime.UTC).day != 17:
            return

        query = "SELECT puuid, platform, game_name, tag_line FROM lol_accounts"
        rows: list[AccountRow] = await self.bot.pool.fetch(query)

        for row in rows:
            try:
                account = await self.bot.riot.get_account_v1_by_puuid(region=row["platform"], puuid=row["puuid"])
            except aiohttp.ClientResponseError as exc:
                if exc.status == 404:
                    log.info("Failed to get summoner under previous name %s#%s", row["game_name"], row["tag_line"])
                    continue
                else:
                    raise

            if account["gameName"] != row["game_name"] or account["tagLine"] != row["tag_line"]:
                query = """
                    UPDATE lol_accounts
                    SET game_name = $1, tag_line = $2
                    WHERE puuid = $3
                """
                await self.bot.pool.execute(query, account["gameName"], account["tagLine"], account["puuid"])
