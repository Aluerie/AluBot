from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, TypedDict, override

import aiohttp
import asyncpg

from bot import aluloop
from utils import const

from ...base_fpc import BaseNotifications, EditTuple, RecipientTuple
from ..api import game_const, regions
from .models import MatchToEdit, MatchToSend

if TYPE_CHECKING:
    from bot import AluBot

    class LivePlayerAccountRow(TypedDict):
        puuid: str
        player_id: int
        in_game_name: str
        tag_line: str
        platform: str
        display_name: str
        twitch_id: str
        last_edited: int

    class FindMatchesToEditQueryRow(TypedDict):
        match_id: int
        champion_id: int
        platform: regions.LiteralPlatform
        channel_message_tuples: list[tuple[int, int]]

    class GetRecipientsQueryRow(TypedDict):
        channel_id: int
        spoil: bool


__all__ = ("Notifications",)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class Notifications(BaseNotifications):
    def __init__(self, bot: AluBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, "lol", *args, **kwargs)
        self.live_match_ids: list[int] = []

    @override
    async def cog_load(self) -> None:
        self.notification_worker.add_exception_type(asyncpg.InternalServerError)
        self.notification_worker.clear_exception_types()
        self.notification_worker.start()
        return await super().cog_load()

    @override
    async def cog_unload(self) -> None:
        self.notification_worker.stop()  # .cancel()
        return await super().cog_unload()

    async def send_notifications(self) -> None:
        self.live_match_ids = []

        query = "SELECT DISTINCT character_id FROM lol_favourite_characters"
        favourite_champion_ids = [r for (r,) in await self.bot.pool.fetch(query)]  # row.unnest

        query = "SELECT DISTINCT player_id FROM lol_favourite_players"
        favourite_player_ids = [r for (r,) in await self.bot.pool.fetch(query)]
        player_streams = await self.get_player_streams(const.Twitch.LOL_GAME_CATEGORY_ID, favourite_player_ids)

        query = """
            SELECT a.puuid, a.player_id, in_game_name, tag_line, platform, display_name, twitch_id, last_edited
            FROM lol_accounts a
            JOIN lol_players p ON a.player_id = p.player_id
            WHERE p.player_id=ANY($1)
        """
        player_account_rows: list[LivePlayerAccountRow] = await self.bot.pool.fetch(query, player_streams.keys())

        # todo: bring pulsefire TaskGroup here
        # I'm not sure how to combine `player_account_rows` with results from Semaphore though.
        # https://pulsefire.iann838.com/usage/advanced/concurrent-requests/
        for player_account_row in player_account_rows:
            try:
                game = await self.bot.lol.get_lol_spectator_v5_active_game_by_summoner(
                    puuid=player_account_row["puuid"],
                    region=player_account_row["platform"],
                )
            except aiohttp.ClientResponseError as exc:
                # we have to do try/except because discord.ext.tasks has aiohttp errors as
                # _valid_exceptions which means it just restarts the loop instead of raising the error
                # and pulsefire unfortunately raises aiohttp errors.
                # I do not to remove them from valid_exceptions.
                if exc.status == 404:
                    log.debug(
                        "%s is not in the active game on account %s#%s",
                        player_account_row["display_name"],
                        player_account_row["in_game_name"],
                        player_account_row["tag_line"],
                    )
                else:
                    log.warning(
                        "`lol_spectator_v4_active_game_by_summoner` failed with %s for %s#%s",
                        exc.status,
                        player_account_row["in_game_name"],
                        player_account_row["tag_line"],
                    )
                continue

            # continue game analysis
            if game["gameQueueConfigId"] != game_const.SOLO_RANKED_5v5_QUEUE_ENUM:
                continue

            self.live_match_ids.append(game["gameId"])

            participant = next((p for p in game["participants"] if p["puuid"] == player_account_row["puuid"]), None)

            if (
                participant
                and participant["championId"] in favourite_champion_ids
                and player_account_row["last_edited"] != game["gameId"]
            ):
                query = """
                    SELECT s.channel_id, s.spoil
                    FROM lol_favourite_characters c
                    JOIN lol_favourite_players p on c.guild_id = p.guild_id
                    JOIN lol_settings s on s.guild_id = c.guild_id
                    WHERE character_id=$1
                        AND player_id=$2
                        AND NOT channel_id=ANY(SELECT channel_id FROM lol_messages WHERE match_id=$3)
                        AND s.enabled = TRUE;
                """
                rows: list[GetRecipientsQueryRow] = await self.bot.pool.fetch(
                    query,
                    participant["championId"],
                    player_account_row["player_id"],
                    game["gameId"],
                )

                if rows:
                    champion = await self.bot.lol.champions.by_id(participant["championId"])
                    log.info(
                        "Sending `%s_%s` - [`%s`](%s) %s",
                        game["platformId"],
                        game["gameId"],
                        player_account_row["display_name"],
                        (
                            f"https://op.gg/summoners/{player_account_row['platform']}/"
                            f"{player_account_row['in_game_name']}-{player_account_row['tag_line']}"
                        ),
                        champion.emote,
                    )
                    match_to_send = MatchToSend(self.bot, game, participant, player_account_row, champion)
                    await self.send_match(
                        match_to_send,
                        [RecipientTuple(channel_id=row["channel_id"], spoil=row["spoil"]) for row in rows],
                    )

    @aluloop(seconds=59)
    async def notification_worker(self) -> None:
        log.debug("--- League FPC Notifications Task is starting now ---")
        await self.send_notifications()
        await self.edit_notifications()
        log.debug("--- League FPC Notifications Task is finished ---")

    # POST MATCH EDITS

    async def edit_notifications(self) -> None:
        query = """
            SELECT match_id, champion_id, platform, ARRAY_AGG ((channel_id, message_id)) channel_message_tuples
            FROM lol_messages
            WHERE NOT match_id=ANY($1)
            GROUP BY match_id, champion_id, platform
        """
        match_rows: list[FindMatchesToEditQueryRow] = await self.bot.pool.fetch(query, self.live_match_ids)

        for match_row in match_rows:
            try:
                match_id = f"{match_row['platform'].upper()}_{match_row['match_id']}"
                continent = regions.Platform(match_row["platform"]).continent

                match = await self.bot.lol.get_lol_match_v5_match(id=match_id, region=continent)
                timeline = await self.bot.lol.get_lol_match_v5_match_timeline(id=match_id, region=continent)

            except aiohttp.ClientResponseError as exc:
                if exc.status == 404:
                    continue
                raise

            for participant in match["info"]["participants"]:
                if participant["championId"] == match_row["champion_id"]:
                    # found our participant
                    match_to_edit = MatchToEdit(self.bot, participant=participant, timeline=timeline)
                    await self.edit_match(
                        match_to_edit,
                        [
                            EditTuple(channel_id=channel_id, message_id=message_id)
                            for channel_id, message_id in match_row["channel_message_tuples"]
                        ],
                    )
            query = "DELETE FROM lol_messages WHERE match_id=$1"
            await self.bot.pool.fetch(query, match_row["match_id"])


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Notifications(bot))
