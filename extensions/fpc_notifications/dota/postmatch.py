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

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class DotaPostMatchEdit(FPCCog):
    def __init__(self, bot: AluBot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.postmatch_players: list[PostMatchPlayerData] = []
        self.opendota_req_cache: dict[int, OpendotaRequestMatch] = dict()

    async def cog_load(self) -> None:
        self.bot.initiate_steam_dota()
        self.postmatch_edits.start()
        self.daily_report.start()
        return await super().cog_load()

    async def cog_unload(self) -> None:
        self.postmatch_edits.stop()  # .cancel()
        self.daily_report.stop()  # .cancel()
        return await super().cog_unload()

    async def fill_postmatch_players(self):
        self.postmatch_players = []

        query = "SELECT * FROM dota_matches WHERE is_finished=TRUE"
        for row in await self.bot.pool.fetch(query):
            if row.match_id not in self.opendota_req_cache:
                self.opendota_req_cache[row.match_id] = OpendotaRequestMatch(row.match_id, row.opendota_jobid)

            cache_item: OpendotaRequestMatch = self.opendota_req_cache[row.match_id]

            if pl_dict_list := await cache_item.workflow(self.bot):
                query = "SELECT * FROM dota_messages WHERE match_id=$1"
                for r in await self.bot.pool.fetch(query, row.match_id):
                    for player in pl_dict_list:
                        if player["hero_id"] == r.character_id:
                            self.postmatch_players.append(
                                PostMatchPlayerData(
                                    player_data=player,
                                    channel_id=r.channel_id,
                                    message_id=r.message_id,
                                    twitch_status=r.twitch_status,
                                    api_calls_done=cache_item.api_calls_done,
                                )
                            )
            if cache_item.dict_ready:
                self.opendota_req_cache.pop(row.match_id)
                query = "DELETE FROM dota_matches WHERE match_id=$1"
                await self.bot.pool.execute(query, row.match_id)

    @aluloop(minutes=1)
    async def postmatch_edits(self):
        # log.debug('AG | --- Task is starting now ---')
        await self.fill_postmatch_players()
        for player in self.postmatch_players:
            await player.edit_the_embed(self.bot)
        # log.debug('AG | --- Task is finished ---')

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
