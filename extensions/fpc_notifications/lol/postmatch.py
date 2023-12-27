from __future__ import annotations

import logging
from typing import TYPE_CHECKING, NamedTuple

import aiohttp
from discord.ext import commands
from pulsefire.clients import RiotAPIClient

import config

from .._base import FPCCog
from ._models import PostMatchPlayer

if TYPE_CHECKING:
    from .notifications import LoLMatchRecord

    class LoLMessageRecord(NamedTuple):
        message_id: int
        channel_id: int
        match_id: int
        champ_id: int


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class LoLFeedPostMatchEdit(FPCCog):
    @commands.Cog.listener("on_lol_fpc_notification_match_finished")
    async def edit_lol_notification_messages(self, match_rows: list[LoLMatchRecord]):
        for match_row in match_rows:
            try:
                async with RiotAPIClient(default_headers={"X-Riot-Token": config.RIOT_API_KEY}) as riot_api_client:
                    match = await riot_api_client.get_lol_match_v5_match(
                        id=f"{match_row.platform.upper()}_{match_row.match_id}",
                        region=match_row.region,
                    )
            except aiohttp.ClientResponseError as exc:
                if exc.status == 404:
                    continue
                else:
                    raise

            query = "SELECT * FROM lol_messages WHERE match_id=$1"
            message_rows: list[LoLMessageRecord] = await self.bot.pool.fetch(query, match_row.match_id)

            for message_row in message_rows:
                participant = next(p for p in match["info"]["participants"] if p["championId"] == message_row.champ_id)
                post_match_player = PostMatchPlayer(
                    channel_id=message_row.channel_id,
                    message_id=message_row.message_id,
                    summoner_id=participant["summonerId"],
                    kda=f"{participant['kills']}/{participant['deaths']}/{participant['assists']}",
                    outcome="Win" if participant["win"] else "Loss",
                    item_ids=[participant[f"item{i}"] for i in range(0, 6 + 1)],
                )
                await post_match_player.edit_notification_embed(self.bot)
            query = "DELETE FROM lol_matches WHERE match_id=$1"
            await self.bot.pool.fetch(query, match_row.match_id)


async def setup(bot):
    await bot.add_cog(LoLFeedPostMatchEdit(bot))
