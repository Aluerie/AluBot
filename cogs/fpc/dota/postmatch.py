from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, Dict, List

import discord
from discord.ext import commands, tasks

from utils import AluCog, Clr, MClr

from ._models import OpendotaRequestMatch, PostMatchPlayerData

if TYPE_CHECKING:
    from utils import AluBot, AluContext

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class DotaPostMatchEdit(AluCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.postmatch_players: List[PostMatchPlayerData] = []
        self.opendota_req_cache: Dict[int, OpendotaRequestMatch] = dict()

    async def cog_load(self) -> None:
        self.bot.ini_steam_dota()
        self.postmatch_edits.start()
        self.daily_report.start()

    async def cog_unload(self) -> None:
        self.postmatch_edits.stop()  # .cancel()
        self.daily_report.stop()  # .cancel()

    async def fill_postmatch_players(self):
        self.postmatch_players = []

        query = "SELECT * FROM dota_matches WHERE is_finished=TRUE"
        for row in await self.bot.pool.fetch(query):
            if row.id not in self.opendota_req_cache:
                self.opendota_req_cache[row.id] = OpendotaRequestMatch(row.id, row.opendota_jobid)

            cache_item: OpendotaRequestMatch = self.opendota_req_cache[row.id]

            if pl_dict_list := await cache_item.workflow(self.bot):
                query = "SELECT * FROM dota_messages WHERE match_id=$1"
                for r in await self.bot.pool.fetch(query, row.id):
                    for player in pl_dict_list:
                        if player["hero_id"] == r.hero_id:
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
                self.opendota_req_cache.pop(row.id)
                query = "DELETE FROM dota_matches WHERE id=$1"
                await self.bot.pool.execute(query, row.id)

    @tasks.loop(minutes=1)
    async def postmatch_edits(self):
        # log.debug('AG | --- Task is starting now ---')
        await self.fill_postmatch_players()
        for player in self.postmatch_players:
            await player.edit_the_embed(self.bot)
        # log.debug('AG | --- Task is finished ---')

    @postmatch_edits.before_loop
    async def postmatch_edits_before(self):
        await self.bot.wait_until_ready()

    @postmatch_edits.error
    async def postmatch_edits_error(self, error):
        await self.bot.send_traceback(error, where="DotaFeed PostGameEdit")
        # self.dotafeed.restart()

    @commands.command(hidden=True, aliases=["odrl", "od_rl", "odota_ratelimit"])
    async def opendota_ratelimit(self, ctx: AluContext):
        """Send opendota rate limit numbers"""
        e = discord.Embed(colour=Clr.prpl, description=f"Odota limits: {self.bot.odota_ratelimit}")
        await ctx.reply(embed=e)

    @tasks.loop(time=datetime.time(hour=2, minute=51, tzinfo=datetime.timezone.utc))
    async def daily_report(self):
        e = discord.Embed(title="Daily Report", colour=MClr.black())
        the_dict = self.bot.odota_ratelimit
        month, minute = int(the_dict['monthly']), int(the_dict['minutely'])
        e.description = f"Odota limits. monthly: {month} minutely: {minute}"
        content = f'{self.bot.owner_id}' if month < 10_000 else ''
        await self.hideout.daily_report.send(content=content, embed=e)  # type: ignore

    @daily_report.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot: AluBot):
    await bot.add_cog(DotaPostMatchEdit(bot))
