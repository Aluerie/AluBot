from __future__ import annotations

import datetime
import logging
import time
from typing import TYPE_CHECKING, MutableMapping, TypedDict

import aiohttp
import asyncpg
import discord
import orjson
from discord.ext import commands

import config
from utils import aluloop, const

from .._base import FPCCog
from ._models import DotaFPCMatchToEditWithOpenDota, DotaFPCMatchToEditWithStratz, DotaFPCMatchToSend

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluContext

    class DotaFPCMessage(TypedDict):
        match_id: int
        friend_id: int
        message_id: int
        channel_id: int
        hero_id: int

    class AnalyzeTopSourceResponsePlayerQueryRow(TypedDict):
        player_id: int
        display_name: str
        twitch_id: int

    class MatchToEditSubDict(TypedDict):
        hero_id: int
        loop_count: int
        edited_with_opendota: bool
        edited_with_stratz: bool
        channel_message_tuples: set[tuple[int, int]]

    type MatchToEdit = dict[tuple[int, int], MatchToEditSubDict]

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
        self.matches_to_edit: MatchToEdit = {}
        self.stratz_daily_remaining_ratelimit: str = "Not set yet"
        self.stratz_daily_total_ratelimit: str = "Not set yet"

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

        self.daily_ratelimit_report.start()
        return await super().cog_load()

    @commands.Cog.listener()
    async def on_my_top_games_response(self):
        print("double u tea ef ef")

    async def cog_unload(self) -> None:
        self.task_to_send_dota_fpc_messages.cancel()
        self.task_to_edit_dota_fpc_messages.cancel()
        self.daily_ratelimit_report.stop()
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
                    WHERE character_id=$1 
                        AND p.player_id=$2
                        AND NOT s.channel_id = ANY(
                            SELECT channel_id 
                            FROM dota_messages 
                            WHERE match_id = $3 AND friend_id=$4
                        );
                """
                channel_ids: list[int] = [
                    channel_id
                    for channel_id, in await self.bot.pool.fetch(
                        query, player.hero_id, user["player_id"], match.match_id, player.account_id
                    )
                ]
                hero_name = await self.bot.dota_cache.hero.name_by_id(player.hero_id)
                log.debug("%s - %s", user["display_name"], hero_name)

                if channel_ids:
                    hero_ids = [p.hero_id for p in sorted(match.players, key=lambda x: (x.team, x.team_slot))]
                    self.live_matches.append(
                        DotaFPCMatchToSend(
                            match_id=match.match_id,
                            friend_id=player.account_id,
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

            message = await channel.send(embed=embed, file=image_file)
            log.debug("Notification was succesfully sent")

            query = """
                INSERT INTO dota_messages (message_id, channel_id, match_id, friend_id, hero_id) 
                VALUES ($1, $2, $3, $4, $5)
            """
            await self.bot.pool.execute(query, message.id, channel.id, match.match_id, match.friend_id, match.hero_id)

    async def declare_matches_finished(self):
        if not self.allow_editing_matches:
            # then we don't need this :D
            return

        log.debug("Declaring finished matches")
        query = "SELECT * FROM dota_messages WHERE NOT match_id=ANY($1)"
        finished_match_rows: list[DotaFPCMessage] = await self.bot.pool.fetch(query, list(self.top_source_dict.keys()))

        for match_row in finished_match_rows:
            uuid_tuple = (match_row["match_id"], match_row["friend_id"])
            message_tuple = (match_row["channel_id"], match_row["message_id"])
            if uuid_tuple not in self.matches_to_edit:
                self.matches_to_edit[uuid_tuple] = {
                    "hero_id": match_row["hero_id"],
                    "loop_count": 0,
                    "edited_with_opendota": False,
                    "edited_with_stratz": False,
                    "channel_message_tuples": set([message_tuple]),
                }
            else:
                self.matches_to_edit[uuid_tuple]["channel_message_tuples"].add(message_tuple)

        if self.matches_to_edit and not self.task_to_edit_dota_fpc_messages.is_running():
            self.task_to_edit_dota_fpc_messages.start()

    @aluloop(seconds=59)
    async def task_to_send_dota_fpc_messages(self):
        log.debug(f"--- Task is starting now ---")

        await self.preliminary_queries()
        self.top_source_dict = {}

        start_time = time.perf_counter()
        log.debug("calling request_top_source NOW ---")
        log.debug('Steam is connected: %s', self.bot.steam.connected)
        # await self.bot.steam_dota_login()
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
    async def edit_with_opendota(
        self, match_id: int, friend_id: int, hero_id: int, channel_message_tuples: set[tuple[int, int]]
    ) -> bool:
        async with self.bot.acquire_opendota_client() as opendota_client:
            try:
                match = await opendota_client.get_match(match_id=match_id)
            except aiohttp.ClientResponseError as exc:
                log.debug("Stratz API Response Not OK with status %s", exc.status)
                return False

            if not match.get("radiant_win"):
                # Somebody abandoned before the first blood or so game didn't count
                await self.cleanup_match_to_edit(match_id, friend_id)
                return True

            for player in match["players"]:
                if player["hero_id"] == hero_id:
                    opendota_player = player
                    break
            else:
                raise RuntimeError(f"Somehow the player {friend_id} is not in the match {match_id}")

            match_to_edit_with_opendota = DotaFPCMatchToEditWithOpenDota(
                self.bot,
                player=opendota_player,
                channel_message_tuples=channel_message_tuples,
            )
            await match_to_edit_with_opendota.edit_notification_embed()
            return True

    async def edit_with_stratz(
        self, match_id: int, friend_id: int, channel_message_tuples: set[tuple[int, int]]
    ) -> bool:
        query = f"""{{
            match(id: {match_id}) {{
                players(steamAccountId: {friend_id}) {{
                    item0Id
                    item1Id
                    item2Id
                    item3Id
                    item4Id
                    item5Id
                    playbackData {{
                        purchaseEvents {{
                            time
                            itemId
                        }}
                    }}
                    stats {{
                        matchPlayerBuffEvent {{
                            itemId
                        }}
                    }}
                }}
            }}
        }}
        """

        async with self.bot.session.post(
            "https://api.stratz.com/graphql",
            headers={
                "Authorization": f"Bearer {config.STRATZ_BEARER_TOKEN}",
                "Content-Type": "application/json",
            },
            json={"query": query},
        ) as response:
            self.stratz_daily_remaining_ratelimit = response.headers["X-RateLimit-Remaining-Day"]
            self.stratz_daily_total_ratelimit = response.headers["X-RateLimit-Limit-Day"]

            if not response.ok:
                log.debug("Stratz API Response Not OK with status %s", response.status)
                return False

            player_data: _schemas.StratzEditFPCMessageGraphQLSchema.ResponseDict = await response.json(
                loads=orjson.loads
            )

            if player_data["data"]["match"] is None:
                # if somebody abandons in draft but we managed to send the game out
                # then parser will fail and declare None
                return True

            # we are ready to send the notification
            fpc_match_to_edit = DotaFPCMatchToEditWithStratz(
                self.bot,
                player=player_data["data"]["match"]["players"][0],
                channel_message_tuples=channel_message_tuples,
            )
            await fpc_match_to_edit.edit_notification_embed()
            return True

    async def cleanup_match_to_edit(self, match_id: int, friend_id: int):
        """Remove match from `self.matches_to_edit` and database."""
        self.matches_to_edit.pop((match_id, friend_id))
        query = "DELETE FROM dota_messages WHERE match_id=$1 AND friend_id=$2"
        await self.bot.pool.execute(query, match_id, friend_id)

    @aluloop(minutes=5)
    async def task_to_edit_dota_fpc_messages(self):
        """Task responsible for editing Dota FPC Messages with PostMatch Result data

        The data is featured from opendota. The parsing is requested if data is not ready.
        """

        log.debug("*** Starting Task to Edit Dota FPC Messages ***")

        for tuple_uuid in list(self.matches_to_edit):
            match_id, friend_id = tuple_uuid

            self.matches_to_edit[tuple_uuid]["loop_count"] += 1
            match_to_edit = self.matches_to_edit[tuple_uuid]

            if match_to_edit["loop_count"] == 1:
                # skip the first iteration so OpenDota can catch-up on the data in next 5 minutes.
                # usually it's obviously behind Game Coordinator so first loop always fails anyway
                continue
            elif match_to_edit["loop_count"] > 15:
                # we had enough of fails with this match, let's move on.
                await self.cleanup_match_to_edit(match_id, friend_id)
                await self.hideout.spam.send(f"Failed to edit the match {match_id} with Opendota or Stratz.")
            else:
                # let's try editing
                # OPENDOTA
                if not match_to_edit["edited_with_opendota"]:
                    match_to_edit["edited_with_opendota"] = await self.edit_with_opendota(
                        match_id, friend_id, match_to_edit["hero_id"], match_to_edit["channel_message_tuples"]
                    )
                # STRATZ
                elif not match_to_edit["edited_with_stratz"]:
                    match_to_edit["edited_with_stratz"] = await self.edit_with_stratz(
                        match_id, friend_id, match_to_edit["channel_message_tuples"]
                    )

                if match_to_edit["edited_with_stratz"] and match_to_edit["edited_with_opendota"]:
                    await self.cleanup_match_to_edit(match_id, friend_id)
                    log.info("Success: after %s loops we edited the message", match_to_edit["loop_count"])

        log.debug("*** Finished Task to Edit Dota FPC Messages ***")

    @task_to_edit_dota_fpc_messages.after_loop
    async def stop_editing_task(self):
        if not self.matches_to_edit:
            # nothing more to analyze
            self.task_to_edit_dota_fpc_messages.cancel()

        if self.task_to_edit_dota_fpc_messages.failed():
            # in case of Exception let's disallow the task at all
            self.allow_editing_matches = False

    # STRATZ RATE LIMITS

    def get_ratelimit_embed(self) -> discord.Embed:
        return (
            discord.Embed(colour=discord.Colour.blue(), title="Daily Remaining RateLimits")
            .add_field(
                name="Stratz", value=f"{self.stratz_daily_remaining_ratelimit}/{self.stratz_daily_total_ratelimit}"
            )
            .add_field(name="OpenDota", value=self.bot.daily_opendota_ratelimit)
        )

    @commands.command(hidden=True)
    async def ratelimits(self, ctx: AluContext):
        """Send OpenDota/Stratz rate limit numbers"""
        await ctx.reply(embed=self.get_ratelimit_embed())

    @aluloop(time=datetime.time(hour=2, minute=51, tzinfo=datetime.timezone.utc))
    async def daily_ratelimit_report(self):
        """Send information about Stratz daily limit to spam logs.

        Stratz has daily ratelimit of 10000 requests and it's kinda scary one, if parsing requests fail a lot.
        This is why we also send @mention if ratelimit is critically low.
        """
        content = ""
        try:
            if int(self.bot.daily_opendota_ratelimit) < 500 or int(self.stratz_daily_remaining_ratelimit) < 1_000:
                content = f"<@{self.bot.owner_id}>"
        except ValueError:
            # I guess, whatever ?
            return

        await self.hideout.daily_report.send(content=content, embed=self.get_ratelimit_embed())


async def setup(bot):
    await bot.add_cog(DotaFPCNotifications(bot))
