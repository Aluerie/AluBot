from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, TypedDict, override

import aiohttp

from bot import AluCog, aluloop

if TYPE_CHECKING:

    class AccountRow(TypedDict):
        puuid: str
        platform: str
        in_game_name: str
        tag_line: str


__all__ = ("SummonerNameCheck",)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class SummonerNameCheck(AluCog):
    """Summoner Name Check."""

    @override
    async def cog_load(self) -> None:
        self.check_summoner_renames.start()
        return await super().cog_load()

    @aluloop(time=datetime.time(hour=12, minute=11, tzinfo=datetime.UTC))
    async def check_summoner_renames(self) -> None:
        """Task that keeps League in-game names in the database somewhat up to date.

        These names are only present for cosmetic purposes.
        But it's nice to be able to search in sites like opgg with ease.
        """
        if datetime.datetime.now(datetime.UTC).day % 3 == 0:
            return

        query = "SELECT puuid, platform, in_game_name, tag_line FROM lol_accounts"
        rows: list[AccountRow] = await self.bot.pool.fetch(query)

        for row in rows:
            try:
                account = await self.bot.lol.get_account_v1_by_puuid(region=row["platform"], puuid=row["puuid"])
            except aiohttp.ClientResponseError as exc:
                if exc.status == 404:
                    log.info("Failed to get summoner under previous name %s#%s", row["in_game_name"], row["tag_line"])
                    continue
                raise

            if account["gameName"] != row["in_game_name"] or account["tagLine"] != row["tag_line"]:
                query = """
                    UPDATE lol_accounts
                    SET in_game_name = $1, tag_line = $2
                    WHERE puuid = $3
                """
                await self.bot.pool.execute(query, account["gameName"], account["tagLine"], account["puuid"])
