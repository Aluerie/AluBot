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

from .._fpc_utils import FPCNotificationsBase
from ._models import (
    DotaFPCMatchToEditNotCounted,
    DotaFPCMatchToEditWithOpenDota,
    DotaFPCMatchToEditWithStratz,
    DotaFPCMatchToSend,
)

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluContext

    class AnalyzeGetPlayerIDsQueryRow(TypedDict):
        twitch_live_only: bool
        player_ids: list[int]

    from .._fpc_utils.base_notifications import ChannelSpoilQueryRow

    class FindMatchesToEditQueryRow(TypedDict):
        match_id: int
        friend_id: int
        hero_id: int
        channel_message_tuples: list[tuple[int, int]]

    class AnalyzeTopSourceResponsePlayerQueryRow(TypedDict):
        player_id: int
        display_name: str
        twitch_id: int

    class MatchToEditSubDict(TypedDict):
        hero_id: int
        loop_count: int
        edited_with_opendota: bool
        edited_with_stratz: bool
        channel_message_tuples: list[tuple[int, int]]

    type MatchToEdit = dict[tuple[int, int], MatchToEditSubDict]

    from . import _schemas


send_log = logging.getLogger("send_dota_fpc")
send_log.setLevel(logging.DEBUG)

edit_log = logging.getLogger("edit_dota_fpc")
edit_log.setLevel(logging.DEBUG)


class DotaFPCNotifications(FPCNotificationsBase):
    def __init__(self, bot: AluBot, *args, **kwargs):
        super().__init__(bot, prefix="dota", *args, **kwargs)
        # Send Matches related attrs
        self.lobby_ids: set[int] = set()
        self.top_source_dict: MutableMapping[int, _schemas.CSourceTVGameSmall] = {}
        self.live_matches: list[DotaFPCMatchToSend] = []
        self.hero_fav_ids: list[int] = []
        self.player_fav_ids: list[int] = []

        # Edit Matches related attrs
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
                    send_log.debug("top_source_dict is ready: Emitting my_top_games_response")
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

    def request_top_source(self):
        self.bot.dota.request_top_source_tv_games(start_game=90)
        # there we are essentially blocking the bot which is bad
        # import asyncio
        self.bot.dota.wait_event("my_top_games_response", timeout=8)

        # the hack that does not work
        # await asyncio.sleep(4)
        # await self.bot.wait_for('my_top_games_response', timeout=4)
        # also idea with asyncio.Event() or checking if top_source_dict is populated

    async def convert_player_id_to_friend_id(self, player_ids: list[int]) -> list[int]:
        query = "SELECT friend_id FROM dota_accounts WHERE player_id=ANY($1)"
        return [f for f, in await self.bot.pool.fetch(query, player_ids)]

    async def analyze_top_source_response(self):
        self.live_matches = []

        query = "SELECT DISTINCT character_id FROM dota_favourite_characters"
        favourite_hero_ids: list[int] = [r for r, in await self.bot.pool.fetch(query)]

        query = """
            SELECT twitch_live_only, ARRAY_AGG(player_id) player_ids
            FROM dota_favourite_players p
            JOIN dota_settings s ON s.guild_id = p.guild_id
            WHERE s.enabled = TRUE
            GROUP by twitch_live_only
        """
        player_id_rows: list[AnalyzeGetPlayerIDsQueryRow] = await self.bot.pool.fetch(query)

        friend_id_cache: dict[bool, list[int]] = {True: [], False: []}
        for row in player_id_rows:
            if row["twitch_live_only"]:
                # need to check what streamers are live
                twitch_live_player_ids = await self.get_twitch_live_player_ids(
                    const.Twitch.DOTA_GAME_CATEGORY_ID, row["player_ids"]
                )
                friend_id_cache[True] = await self.convert_player_id_to_friend_id(twitch_live_player_ids)
            else:
                friend_id_cache[False] = await self.convert_player_id_to_friend_id(row["player_ids"])

        for match in self.top_source_dict.values():
            for twitch_live_only, friend_ids in friend_id_cache.items():
                our_players = [
                    p for p in match.players if p.account_id in friend_ids and p.hero_id in favourite_hero_ids
                ]
                for player in our_players:
                    query = """
                        SELECT player_id, display_name, twitch_id 
                        FROM dota_players 
                        WHERE player_id=(SELECT player_id FROM dota_accounts WHERE friend_id=$1)
                    """
                    user: AnalyzeTopSourceResponsePlayerQueryRow = await self.bot.pool.fetchrow(
                        query, player.account_id
                    )
                    query = """
                        SELECT s.channel_id, s.spoil
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
                            AND s.twitch_live_only = $5
                            AND s.enabled = TRUE
                    """

                    channel_spoil_tuples: list[tuple[int, bool]] = [
                        (channel_id, spoil)
                        for channel_id, spoil in await self.bot.pool.fetch(
                            query,
                            player.hero_id,
                            user["player_id"],
                            match.match_id,
                            player.account_id,
                            twitch_live_only,
                        )
                    ]

                    if channel_spoil_tuples:
                        hero_name = await self.bot.dota_cache.hero.name_by_id(player.hero_id)
                        send_log.debug("%s - %s", user["display_name"], hero_name)
                        hero_ids = [p.hero_id for p in sorted(match.players, key=lambda x: (x.team, x.team_slot))]
                        match_to_send = DotaFPCMatchToSend(
                            self.bot,
                            match_id=match.match_id,
                            friend_id=player.account_id,
                            start_time=match.activate_time,
                            player_name=user["display_name"],
                            twitch_id=user["twitch_id"],
                            hero_id=player.hero_id,
                            hero_ids=hero_ids,
                            server_steam_id=match.server_steam_id,
                            hero_name=hero_name,
                        )
                        # SENDING
                        start_time = time.perf_counter()
                        await self.send_notifications(match_to_send, channel_spoil_tuples)
                        send_log.debug("Sending took %.5f secs", time.perf_counter() - start_time)

    async def mark_matches_to_edit(self):
        send_log.debug("Declaring finished matches")
        query = """
            SELECT match_id, friend_id, hero_id, ARRAY_AGG ((message_id, m.channel_id)) channel_message_tuples
            FROM dota_messages
            WHERE NOT match_id=ANY($1)
            GROUP BY match_id, friend_id, hero_id
        """
        current_match_to_edit_ids = [key[0] for key in self.matches_to_edit]
        currently_live_match_ids = list(self.top_source_dict.keys())

        finished_match_rows: list[FindMatchesToEditQueryRow] = await self.bot.pool.fetch(
            query, current_match_to_edit_ids + currently_live_match_ids
        )

        for match_row in finished_match_rows:
            self.matches_to_edit[(match_row["match_id"], match_row["friend_id"])] = {
                "hero_id": match_row["hero_id"],
                "channel_message_tuples": match_row["channel_message_tuples"],
                "loop_count": 0,
                "edited_with_opendota": False,
                "edited_with_stratz": False,
            }

        edit_log.debug(self.matches_to_edit)
        if self.matches_to_edit and not self.task_to_edit_dota_fpc_messages.is_running():
            self.task_to_edit_dota_fpc_messages.start()

    @aluloop(seconds=59)
    async def task_to_send_dota_fpc_messages(self):
        send_log.debug(f"--- Task is starting now ---")

        self.top_source_dict = {}

        # REQUESTING
        start_time = time.perf_counter()
        send_log.debug("Calling request_top_source NOW ---")
        send_log.debug("Steam is connected: %s", self.bot.steam.connected)
        # await self.bot.steam_dota_login()
        self.request_top_source()
        # await self.bot.loop.run_in_executor(None, self.request_top_source, args)
        # res = await asyncio.to_thread(self.request_top_source)
        top_source_end_time = time.perf_counter() - start_time
        send_log.debug("Requesting took %.5f secs with %s results", top_source_end_time, len(self.top_source_dict))

        # ANALYZING
        start_time = time.perf_counter()
        await self.analyze_top_source_response()
        send_log.debug(
            "Analyzing took %.5f secs with %s live matches", time.perf_counter() - start_time, len(self.live_matches)
        )

        if top_source_end_time > 8:
            await self.hideout.spam.send("dota notifs is dying")
            # likely spoiled result that gonna ruin "mark_matches_to_edit" so let's return
            return

        # MARKING MATCHES FOR EDIT
        if self.allow_editing_matches:
            start_time = time.perf_counter()
            await self.mark_matches_to_edit()
            send_log.debug(
                "Marking took %.5f secs with %s live matches",
                time.perf_counter() - start_time,
                len(self.matches_to_edit),
            )
        send_log.debug(f"--- Task is finished ---")

    # POST MATCH EDITS
    async def edit_with_opendota(
        self, match_id: int, friend_id: int, hero_id: int, channel_message_tuples: list[tuple[int, int]]
    ) -> bool:
        try:
            opendota_match = await self.bot.opendota_client.get_match(match_id=match_id)
        except aiohttp.ClientResponseError as exc:
            edit_log.debug("OpenDota API Response Not OK with status %s", exc.status)
            return False

        if "radiant_win" not in opendota_match:
            # Somebody abandoned before the first blood or so game didn't count
            # thus "radiant_win" key is not present
            edit_log.debug("The stats for match %s did not count. Deleting the match.", match_id)
            not_counted_match_to_edit = DotaFPCMatchToEditNotCounted(self.bot)
            await self.edit_notifications(not_counted_match_to_edit, channel_message_tuples)
            await self.cleanup_match_to_edit(match_id, friend_id)
            return True

        for player in opendota_match["players"]:
            if player["hero_id"] == hero_id:
                opendota_player = player
                break
        else:
            raise RuntimeError(f"Somehow the player {friend_id} is not in the match {match_id}")

        match_to_edit_with_opendota = DotaFPCMatchToEditWithOpenDota(self.bot, player=opendota_player)
        await self.edit_notifications(match_to_edit_with_opendota, channel_message_tuples)
        return True

    async def edit_with_stratz(
        self, match_id: int, friend_id: int, channel_message_tuples: list[tuple[int, int]]
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
                edit_log.debug("Stratz API Response Not OK with status %s", response.status)
                return False

            stratz_data: _schemas.StratzEditFPCMessageGraphQLSchema.ResponseDict = await response.json(
                loads=orjson.loads
            )

            if stratz_data["data"]["match"] is None:
                # if somebody abandons in draft but we managed to send the game out
                # then parser will fail and declare None
                return True

            # we are ready to send the notification
            fpc_match_to_edit = DotaFPCMatchToEditWithStratz(
                self.bot, player=stratz_data["data"]["match"]["players"][0]
            )
            await self.edit_notifications(fpc_match_to_edit, channel_message_tuples)
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

        edit_log.debug("*** Starting Task to Edit Dota FPC Messages ***")

        for tuple_uuid in list(self.matches_to_edit):
            match_id, friend_id = tuple_uuid

            self.matches_to_edit[tuple_uuid]["loop_count"] += 1
            match_to_edit = self.matches_to_edit[tuple_uuid]
            edit_log.debug("Editing match %s friend %s loop %s", match_id, friend_id, match_to_edit["loop_count"])

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
                    edit_log.debug("OpenDota editing: %s", match_to_edit["edited_with_opendota"])
                # STRATZ
                elif not match_to_edit["edited_with_stratz"]:
                    match_to_edit["edited_with_stratz"] = await self.edit_with_stratz(
                        match_id, friend_id, match_to_edit["channel_message_tuples"]
                    )
                    edit_log.debug("OpenDota editing: %s", match_to_edit["edited_with_stratz"])

                if match_to_edit["edited_with_stratz"] and match_to_edit["edited_with_opendota"]:
                    await self.cleanup_match_to_edit(match_id, friend_id)
                    edit_log.info("Success: after %s loops we edited the message", match_to_edit["loop_count"])

        edit_log.debug("*** Finished Task to Edit Dota FPC Messages ***")

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
                name="Stratz",
                value=f"{self.stratz_daily_remaining_ratelimit}/{self.stratz_daily_total_ratelimit}",
            )
            .add_field(
                name="OpenDota",
                value=self.bot.daily_opendota_ratelimit,
            )
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
