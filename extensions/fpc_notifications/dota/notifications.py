from __future__ import annotations

import datetime
import logging
import time
from typing import TYPE_CHECKING, MutableMapping, TypedDict

import asyncpg
import discord
from discord.ext import commands, tasks
from pulsefire.middlewares import http_error_middleware, json_response_middleware

from utils import aluloop, const, dota

from .._base import FPCCog
from ._models import DotaFPCMatchToEdit, DotaFPCMatchToSend

if TYPE_CHECKING:
    from aiohttp import ClientResponse
    from pulsefire.middlewares import Invocation, MiddlewareCallable

    from bot import AluBot
    from utils import AluContext

    class DotaFPCMessageQueryRow(TypedDict):
        message_id: int
        channel_id: int
        match_id: int
        character_id: int

    class AnalyzeTopSourceResponsePlayerQueryRow(TypedDict):
        player_id: int
        display_name: str
        twitch_id: int

    from . import _schemas


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class DotaFPCNotifications(FPCCog):
    def __init__(self, bot: AluBot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.lobby_ids: set[int] = set()
        self.top_source_dict: MutableMapping[int, _schemas.CSourceTVGameSmall] = {}
        self.live_matches: list[DotaFPCMatchToSend] = []
        self.hero_fav_ids: list[int] = []
        self.player_fav_ids: list[int] = []

        self.is_postmatch_edits_running: bool = True

        self.allow_editing_matches: bool = True
        self.matches_to_edit: dict[int, int] = {}
        self.daily_opendota_ratelimit: str = "not set yet"

    async def cog_load(self) -> None:
        @self.bot.dota.on("top_source_tv_games")  # type: ignore
        def response(result: _schemas.CMsgGCToClientFindTopSourceTVGamesResponse):
            # remember the quirk that
            # result.specific_games = my friends games
            # not result.specific_games = top100 mmr games
            if not result.specific_games:
                # log.debug(
                #     f"top_source_tv_games resp ng: {result.num_games} sg: {result.specific_games} "
                #     f"{result.start_game, result.game_list_index, len(result.game_list)} "
                #     f"{result.game_list[0].players[0].account_id}"
                # )
                for match in result.game_list:
                    self.top_source_dict[match.match_id] = match

                if len(self.top_source_dict) == 100:
                    log.debug("top_source_dict is ready: Emitting my_top_games_response")
                    self.bot.dota.emit("my_top_games_response")
                    # did not work
                    # self.bot.dispatch("my_top_games_response")

        # self.bot.dota.on('top_source_tv_games', response)

        # maybe asyncpg.PostgresConnectionError
        self.task_to_send_dota_fpc_messages.add_exception_type(asyncpg.InternalServerError)
        self.task_to_send_dota_fpc_messages.clear_exception_types()
        self.task_to_send_dota_fpc_messages.start()

        self.task_to_edit_dota_fpc_messages.clear_exception_types()

        self.opendota_daily_ratelimit_report.start()
        return await super().cog_load()

    @commands.Cog.listener()
    async def on_my_top_games_response(self):
        print("double u tea ef ef")

    async def cog_unload(self) -> None:
        self.task_to_send_dota_fpc_messages.cancel()
        self.task_to_edit_dota_fpc_messages.cancel()
        self.opendota_daily_ratelimit_report.stop()
        return await super().cog_unload()

    async def preliminary_queries(self):
        async def get_all_fav_ids(table_name: str, column_name: str) -> list[int]:
            query = f"SELECT DISTINCT {column_name} FROM dota_favourite_{table_name}"
            rows = await self.bot.pool.fetch(query)
            return [r for r, in rows]

        self.hero_fav_ids = await get_all_fav_ids("characters", "character_id")
        self.player_fav_ids = await get_all_fav_ids("players", "player_id")

    def request_top_source(self):
        self.bot.dota.request_top_source_tv_games(start_game=90)
        # there we are essentially blocking the bot which is bad
        # import asyncio
        self.bot.dota.wait_event("my_top_games_response", timeout=8)

        # the hack that does not work
        # await asyncio.sleep(4)
        # await self.bot.wait_for('my_top_games_response', timeout=4)
        # also idea with asyncio.Event() or checking if top_source_dict is populated

    async def analyze_top_source_response(self):
        self.live_matches = []
        query = "SELECT friend_id FROM dota_accounts WHERE player_id=ANY($1)"
        friend_ids = [f for f, in await self.bot.pool.fetch(query, self.player_fav_ids)]

        for match in self.top_source_dict.values():
            our_players = [p for p in match.players if p.account_id in friend_ids and p.hero_id in self.hero_fav_ids]
            for player in our_players:
                query = """
                    SELECT player_id, display_name, twitch_id 
                    FROM dota_players 
                    WHERE player_id=(SELECT player_id FROM dota_accounts WHERE friend_id=$1)
                """
                user: AnalyzeTopSourceResponsePlayerQueryRow = await self.bot.pool.fetchrow(query, player.account_id)
                query = """
                    SELECT s.channel_id
                    FROM dota_favourite_characters c
                    JOIN dota_favourite_players p on c.guild_id = p.guild_id
                    JOIN dota_settings s on s.guild_id = c.guild_id
                    WHERE character_id=$1 AND p.player_id=$2
                    AND NOT s.channel_id=ANY(SELECT channel_id FROM dota_messages WHERE match_id=$3);
                """
                channel_ids: list[int] = [
                    i for i, in await self.bot.pool.fetch(query, player.hero_id, user["player_id"], match.match_id)
                ]
                hero_name = await self.bot.dota_cache.hero.name_by_id(player.hero_id)
                log.debug("%s - %s", user["display_name"], hero_name)

                if channel_ids:
                    hero_ids = [p.hero_id for p in sorted(match.players, key=lambda x: (x.team, x.team_slot))]
                    self.live_matches.append(
                        DotaFPCMatchToSend(
                            match_id=match.match_id,
                            start_time=match.activate_time,
                            player_name=user["display_name"],
                            twitch_id=user["twitch_id"],
                            hero_id=player.hero_id,
                            hero_ids=hero_ids,
                            server_steam_id=match.server_steam_id,
                            channel_ids=channel_ids,
                            hero_name=hero_name,
                        )
                    )

    async def send_notifications(self, match: DotaFPCMatchToSend):
        log.debug("Dota 2 FPC's `send_notifications` is starting")

        embed, image_file = await match.get_embed_and_file(self.bot)

        for channel_id in match.channel_ids:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                log.debug("The channel is None")
                continue

            assert isinstance(channel, discord.TextChannel)
            log.debug("Successfully made embed+file")
            owner_name = channel.guild.owner.display_name if channel.guild.owner else "Somebody"
            embed.title = f"{owner_name}'s fav hero + player spotted"
            message = await channel.send(embed=embed, file=image_file)
            log.debug("Notification was succesfully sent")

            query = """
                INSERT INTO dota_matches (match_id) 
                VALUES ($1) 
                ON CONFLICT DO NOTHING
            """
            await self.bot.pool.execute(query, match.match_id)
            query = """
                INSERT INTO dota_messages (message_id, channel_id, match_id, character_id) 
                VALUES ($1, $2, $3, $4)
            """
            await self.bot.pool.execute(query, message.id, channel.id, match.match_id, match.hero_id)

    async def declare_matches_finished(self):
        log.debug("Declaring finished matches")
        query = """
            SELECT match_id FROM dota_matches 
            WHERE NOT match_id=ANY($1)
        """
        match_ids: list[int] = [r for r, in await self.bot.pool.fetch(query, list(self.top_source_dict.keys()))]

        for match_id in match_ids:
            if match_id not in self.matches_to_edit:
                self.matches_to_edit[match_id] = 0

        if self.matches_to_edit and self.allow_editing_matches and not self.task_to_edit_dota_fpc_messages.is_running():
            self.task_to_edit_dota_fpc_messages.start()

    @aluloop(seconds=59)
    async def task_to_send_dota_fpc_messages(self):
        log.debug(f"--- Task is starting now ---")

        await self.preliminary_queries()
        self.top_source_dict = {}

        start_time = time.perf_counter()
        log.debug("calling request_top_source NOW ---")
        await self.bot.steam_dota_login()
        self.request_top_source()
        # await self.bot.loop.run_in_executor(None, self.request_top_source, args)
        # res = await asyncio.to_thread(self.request_top_source)
        top_source_end_time = time.perf_counter() - start_time
        log.debug("top source request took %s secs with %s results", top_source_end_time, len(self.top_source_dict))

        await self.analyze_top_source_response()
        for match in self.live_matches:
            await self.send_notifications(match)

        if top_source_end_time > 8:
            await self.hideout.spam.send("dota notifs is dying")
            # likely spoiled result that gonna ruin "declare_matches_finished" so let's return
            return

        if self.is_postmatch_edits_running:
            await self.declare_matches_finished()
        log.debug(f"--- Task is finished ---")

    # POST MATCH EDITS

    def set_daily_ratelimit_attr(self):
        def constructor(next: MiddlewareCallable):
            async def middleware(invocation: Invocation):
                response: ClientResponse = await next(invocation)
                daily_ratelimit = response.headers.get("X-Rate-Limit-Remaining-Day")
                if daily_ratelimit is not None:
                    self.daily_opendota_ratelimit = daily_ratelimit

                return response

            return middleware

        return constructor

    @aluloop(minutes=5)
    async def task_to_edit_dota_fpc_messages(self):
        """Task responsible for editing Dota FPC Messages with PostMatch Result data

        The data is featured from opendota. The parsing is requested if data is not ready.
        """

        log.debug("*** Starting Task to Edit Dota FPC Messages ***")
        async with dota.OpenDotaClient(
            middlewares=[
                json_response_middleware(),
                self.set_daily_ratelimit_attr(),
                http_error_middleware(),
            ]
        ) as opendota_client:
            for match_id in list(self.matches_to_edit):
                self.matches_to_edit[match_id] += 1
                loop_count = self.matches_to_edit[match_id]

                if loop_count == 1:
                    # skip the first iteration so opendota can catch-up on the data in next 5 minutes.
                    # usually it's obviously behind Game Coordinator so first loop always fails anyway
                    continue
                elif loop_count > 10:
                    # we had enough of fails with this match, let's move on.
                    await self.cleanup_match_to_edit(match_id)
                    await self.hideout.spam.send(f"Failed to edit the match {match_id} with OpenDota.")
                else:
                    match = await opendota_client.get_match(match_id=match_id)
                    if match["od_data"]["has_parsed"]:
                        # we are ready to send the notification

                        query = "SELECT * FROM dota_messages WHERE match_id=$1"
                        message_rows: list[DotaFPCMessageQueryRow] = await self.bot.pool.fetch(query, match_id)

                        for player in match["players"]:
                            # messages can have different favourite players in the same match
                            # thus we need to loop for players too

                            channel_message_tuples: list[tuple[int, int]] = [
                                (message_row["channel_id"], message_row["message_id"])
                                for message_row in message_rows
                                if player["hero_id"] == message_row["character_id"]
                            ]
                            if channel_message_tuples:
                                match_to_edit = DotaFPCMatchToEdit(
                                    self.bot,
                                    player=player,
                                    channel_message_tuples=channel_message_tuples,
                                )
                                await match_to_edit.edit_notification_embed()
                        await self.cleanup_match_to_edit(match_id)
                        log.info("Success: after %s loops we edited the message", loop_count)
                    else:
                        # need to request parsing of the match and then hopefully next loop we good
                        await opendota_client.request_parse(match_id=match_id)

        log.debug("*** Finished Task to Edit Dota FPC Messages ***")

    async def cleanup_match_to_edit(self, match_id: int):
        """Remove match from `self.matches_to_edit` and database."""
        self.matches_to_edit.pop(match_id)
        query = "DELETE FROM dota_matches WHERE match_id=$1"
        await self.bot.pool.execute(query, match_id)

    @task_to_edit_dota_fpc_messages.after_loop
    async def stop_editing_task(self):
        if not self.matches_to_edit or self.task_to_edit_dota_fpc_messages.failed():
            self.task_to_edit_dota_fpc_messages.cancel()

    # OPENDOTA RATE LIMITS

    @commands.command(hidden=True, aliases=["odrl"])
    async def opendota_daily_ratelimit(self, ctx: AluContext):
        """Send opendota rate limit numbers"""
        embed = discord.Embed(colour=const.Colour.prpl()).add_field(
            name="Opendota Daily RateLimit", value=self.daily_opendota_ratelimit
        )
        await ctx.reply(embed=embed)

    @aluloop(time=datetime.time(hour=2, minute=51, tzinfo=datetime.timezone.utc))
    async def opendota_daily_ratelimit_report(self):
        """Send information about opendota daily limit to spam logs.

        OpenDota has daily ratelimit of 2000 requests and it's kinda scary one, if parsing requests fail a lot.
        This is why we also send @mention if ratelimit is critically low.
        """

        content = f"<@{self.bot.owner_id}>" if int(self.daily_opendota_ratelimit) < 500 else ""
        embed = discord.Embed(
            title="Daily Report",
            colour=const.MaterialPalette.black(),
            description=f"Opendota Daily RateLimit: `{self.daily_opendota_ratelimit}`",
        )
        await self.hideout.daily_report.send(content=content, embed=embed)


async def setup(bot):
    await bot.add_cog(DotaFPCNotifications(bot))
