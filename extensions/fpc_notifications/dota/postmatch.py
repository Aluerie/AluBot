from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from utils import aluloop, const

from .._base import FPCCog
from ._models import PostMatchPlayerData
from ._opendota import OpendotaRequestMatch

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluContext

    from .notifications import DotaFPCMatchRecord

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class DotaPostMatchEdit(FPCCog):
    def __init__(self, bot: AluBot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.opendota_req_cache: dict[int, OpendotaRequestMatch] = dict()

    async def cog_load(self) -> None:
        self.daily_report.start()
        return await super().cog_load()

    async def cog_unload(self) -> None:
        self.daily_report.stop()  # .cancel()
        return await super().cog_unload()

    @commands.Cog.listener("on_dota_fpc_notification_match_finished")
    async def edit_dota_notification_messages(self, match_rows: list[DotaFPCMatchRecord]):
        for match_row in match_rows:
            cache_item = self.opendota_req_cache.get(match_row.match_id, None)

            if not cache_item:
                self.opendota_req_cache[match_row.match_id] = cache_item = OpendotaRequestMatch(
                    match_row.match_id, match_row.opendota_jobid
                )

            player_dict_list = await cache_item.workflow(self.bot)
            if player_dict_list:
                query = "SELECT * FROM dota_messages WHERE match_id=$1"
                for message_row in await self.bot.pool.fetch(query, match_row.match_id):
                    for player in player_dict_list:
                        if player["hero_id"] == message_row.character_id:
                            post_match_player = PostMatchPlayerData(
                                player_data=player,
                                channel_id=message_row.channel_id,
                                message_id=message_row.message_id,
                                twitch_status=message_row.twitch_status,
                                api_calls_done=cache_item.api_calls_done,
                            )
                            await post_match_player.edit_notification_embed(self.bot)
            if cache_item.dict_ready:
                self.opendota_req_cache.pop(match_row.match_id)
                query = "DELETE FROM dota_matches WHERE match_id=$1"
                await self.bot.pool.execute(query, match_row.match_id)

    @commands.command(hidden=True, aliases=["odrl", "od_rl", "odota_ratelimit"])
    async def opendota_ratelimit(self, ctx: AluContext):
        """Send opendota rate limit numbers"""
        e = discord.Embed(colour=const.Colour.prpl(), description=f"Odota limits: {self.bot.odota_ratelimit}")
        await ctx.reply(embed=e)

    @aluloop(time=datetime.time(hour=2, minute=51, tzinfo=datetime.timezone.utc))
    async def daily_report(self):
        e = discord.Embed(title="Daily Report", colour=const.MaterialPalette.black())
        the_dict = self.bot.odota_ratelimit
        month, minute = int(the_dict["monthly"]), int(the_dict["minutely"])
        e.description = f"Odota limits. monthly: {month} minutely: {minute}"
        content = f"{self.bot.owner_id}" if month < 10_000 else ""
        await self.hideout.daily_report.send(content=content, embed=e)  # type: ignore


async def setup(bot: AluBot):
    await bot.add_cog(DotaPostMatchEdit(bot))
