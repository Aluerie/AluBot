from __future__ import annotations

import asyncio
import datetime
import logging
import time
from typing import TYPE_CHECKING, TypedDict

import aiohttp
import discord
from discord.ext import commands

from utils import aluloop, const

from .._base import BaseNotifications
from ._models import (
    MatchToSend,
    NotCountedMatchToEdit,
    StratzMatchToEdit,
)

if TYPE_CHECKING:
    # from steam.ext.dota2 import LiveMatch # VALVE_SWITCH
    from bot import AluBot
    from utils import AluContext
    from utils.dota import LiveMatch

    class AnalyzeGetPlayerIDsQueryRow(TypedDict):
        twitch_live_only: bool
        player_ids: list[int]

    class FindMatchesToEditQueryRow(TypedDict):
        match_id: int
        friend_id: int
        hero_id: int
        channel_message_tuples: list[tuple[int, int]]

    class AnalyzeTopSourceResponsePlayerQueryRow(TypedDict):
        player_id: int
        display_name: str
        twitch_id: int


send_log = logging.getLogger("send_dota_fpc")
send_log.setLevel(logging.INFO)

edit_log = logging.getLogger("edit_dota_fpc")
edit_log.setLevel(logging.DEBUG)


class DotaFPCNotifications(BaseNotifications):
    def __init__(self, bot: AluBot, *args, **kwargs):
        super().__init__(bot, prefix="dota", *args, **kwargs)
        # Send Matches related attrs
        self.death_counter: int = 0
        self.top_live_matches: list[LiveMatch] = []

        # Edit Matches related attrs
        self.retry_mapping: dict[tuple[int, int], int] = {}

    async def cog_load(self) -> None:
        # maybe asyncpg.PostgresConnectionError too
        # self.task_to_send_dota_fpc_messages.add_exception_type(asyncpg.InternalServerError)
        self.notification_sender.clear_exception_types()
        self.notification_sender.start()

        self.notification_editor.clear_exception_types()
        self.notification_editor.start()

        self.daily_ratelimit_report.start()
        return await super().cog_load()

    async def cog_unload(self) -> None:
        self.notification_sender.cancel()
        self.notification_editor.cancel()
        self.daily_ratelimit_report.stop()
        return await super().cog_unload()

    async def convert_player_id_to_friend_id(self, player_ids: list[int]) -> list[int]:
        query = "SELECT friend_id FROM dota_accounts WHERE player_id=ANY($1)"
        return [f for f, in await self.bot.pool.fetch(query, player_ids)]

    async def analyze_top_source_response(self, live_matches: list[LiveMatch]):
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

        for match in live_matches:
            for twitch_live_only, friend_ids in friend_id_cache.items():
                our_players = [p for p in match.players if p.id in friend_ids and p.hero.id in favourite_hero_ids]
                for player in our_players:
                    account_id = player.id
                    hero_id = player.hero.id

                    query = """--sql
                        SELECT player_id, display_name, twitch_id 
                        FROM dota_players 
                        WHERE player_id=(SELECT player_id FROM dota_accounts WHERE friend_id = $1);
                    """
                    user: AnalyzeTopSourceResponsePlayerQueryRow = await self.bot.pool.fetchrow(query, account_id)
                    query = """--sql
                        SELECT s.channel_id, s.spoil
                        FROM dota_favourite_characters c
                        JOIN dota_favourite_players p on c.guild_id = p.guild_id
                        JOIN dota_settings s on s.guild_id = c.guild_id
                        WHERE character_id = $1 
                            AND p.player_id = $2
                            AND NOT s.channel_id = ANY(
                                SELECT channel_id 
                                FROM dota_messages 
                                WHERE match_id = $3 AND friend_id = $4
                            )
                            AND s.twitch_live_only = $5
                            AND s.enabled = TRUE;
                    """

                    channel_spoil_tuples: list[tuple[int, bool]] = [
                        (channel_id, spoil)
                        for channel_id, spoil in await self.bot.pool.fetch(
                            query,
                            hero_id,
                            user["player_id"],
                            match.id,
                            account_id,
                            twitch_live_only,
                        )
                    ]

                    if channel_spoil_tuples:
                        hero_name = await self.bot.cache_dota.hero.name_by_id(hero_id)
                        send_log.debug("%s - %s", user["display_name"], hero_name)
                        match_to_send = MatchToSend(
                            self.bot,
                            match_id=match.id,
                            friend_id=account_id,
                            start_time=match.start_time,
                            player_name=user["display_name"],
                            twitch_id=user["twitch_id"],
                            hero_id=hero_id,
                            hero_ids=[hero.id for hero in match.heroes],
                            server_steam_id=match.server_steam_id,
                            hero_name=hero_name,
                        )
                        # SENDING
                        start_time = time.perf_counter()
                        await self.send_match(match_to_send, channel_spoil_tuples)
                        send_log.debug("Sending took %.5f secs", time.perf_counter() - start_time)

    @aluloop(seconds=59)
    async def notification_sender(self):
        send_log.debug(f"--- Task to send Dota2 FPC Notifications is starting now ---")

        # REQUESTING
        start_time = time.perf_counter()
        try:
            live_matches = await self.bot.dota.top_live_matches()
        except asyncio.TimeoutError:
            self.death_counter += 1
            await self.hideout.spam.send(f"Game Coordinator is dying: count `{self.death_counter}`")
            send_log.warning(f"Game Coordinator is dying: count `{self.death_counter}`")
            # nothing to "mark_matches_to_edit" so let's return
            return
        else:
            self.death_counter = 0

        top_source_end_time = time.perf_counter() - start_time
        send_log.debug("Requesting took %.5f secs with %s results", top_source_end_time, len(live_matches))

        # ANALYZING
        start_time = time.perf_counter()
        await self.analyze_top_source_response(live_matches)
        send_log.debug("Analyzing took %.5f secs", time.perf_counter() - start_time)

        # another mini-death condition
        if len(live_matches) < 90:  # 100
            # this means it returned 80, 70, ..., or even 0 matches. 
            # Thus we consider this result corrupted since it can ruin editing logic.
            # We still forgive 90 though, should be fine.
            send_log.warn("GC only fetched %s matches", len(live_matches))
        else:
            self.top_live_matches = live_matches

        send_log.debug(f"--- Task is finished ---")

    @aluloop(minutes=5)
    async def notification_editor(self):
        """Task responsible for editing Dota FPC Messages with PostMatch Result data

        The data is featured from Opendota/Stratz.
        """
        if not self.top_live_matches:
            return

        edit_log.debug("*** Starting Task to Edit Dota FPC Messages ***")

        query = """
            SELECT match_id, friend_id, hero_id, ARRAY_AGG ((channel_id, message_id)) channel_message_tuples
            FROM dota_messages
            WHERE NOT match_id=ANY($1)
            GROUP BY match_id, friend_id, hero_id
        """
        match_rows: list[FindMatchesToEditQueryRow] = await self.bot.pool.fetch(
            query, [match.id for match in self.top_live_matches]
        )

        for match_row in match_rows:
            tuple_uuid = match_id, friend_id = match_row["match_id"], match_row["friend_id"]
            if tuple_uuid not in self.retry_mapping:
                self.retry_mapping[tuple_uuid] = 1
                # Stratz 99% will not have data in the first 5 minutes so it's just a wasted call
                # Thus lets skip the very first loop #0 (by assigning #1 to loop counter)
                continue

            edit_log.debug("Editing match = %s retry %s", tuple_uuid, self.retry_mapping[tuple_uuid])

            try:
                stratz_data = await self.bot.stratz.get_fpc_match_to_edit(match_id=match_id, friend_id=friend_id)
            except aiohttp.ClientResponseError as exc:
                edit_log.warning(
                    "Stratz API Resp for match `%s` friend `%s`: Not OK, status `%s`", match_id, friend_id, exc.status
                )
                self.retry_mapping[tuple_uuid] += 1
                continue

            if stratz_data["data"]["match"] is None:
                # if somebody abandons in draft but we managed to send the game out
                # then parser will fail and declare None
                edit_log.info("Stratz: match %s did not count. Deleting the match.", match_id)
                match_to_edit = NotCountedMatchToEdit(self.bot)
            elif not stratz_data["data"]["match"]["statsDateTime"]:
                edit_log.warning("Parsing for match %s friend %s was not finished.", match_id, friend_id)
                self.retry_mapping[tuple_uuid] += 1
                continue
            else:
                match_to_edit = StratzMatchToEdit(self.bot, stratz_data)

            await self.edit_match(match_to_edit, match_row["channel_message_tuples"])

            query = "DELETE FROM dota_messages WHERE match_id=$1 AND friend_id=$2"
            await self.bot.pool.execute(query, match_id, friend_id)
            edit_log.info("Edited message after `%s` retries.", self.retry_mapping[tuple_uuid])
            self.retry_mapping.pop(tuple_uuid, None)
        edit_log.debug("*** Finished Task to Edit Dota FPC Messages ***")

    # STRATZ RATE LIMITS

    def get_ratelimit_embed(self) -> discord.Embed:
        return discord.Embed(
            colour=discord.Colour.blue(),
            title="Stratz RateLimits",
            description=self.bot.stratz.rate_limiter.rate_limits_string,
        )

    @commands.command(hidden=True)
    async def ratelimits(self, ctx: AluContext):
        """Send OpenDota/Stratz rate limit numbers"""
        await ctx.reply(embed=self.get_ratelimit_embed())

    @aluloop(time=datetime.time(hour=23, minute=55, tzinfo=datetime.timezone.utc))
    async def daily_ratelimit_report(self):
        """Send information about Stratz daily limit to spam logs.

        Stratz has daily ratelimit of 10000 requests and it's kinda scary one, if parsing requests fail a lot.
        This is why we also send @mention if ratelimit is critically low.
        """

        content = ""
        if self.bot.stratz.rate_limiter.rate_limits_ratio < 0.1:
            content = f"<@{self.bot.owner_id}>"

        await self.hideout.logger.send(content=content, embed=self.get_ratelimit_embed())


async def setup(bot):
    await bot.add_cog(DotaFPCNotifications(bot))
