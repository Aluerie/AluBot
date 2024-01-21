from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypedDict

import aiohttp
import asyncpg
import discord

from utils import aluloop, const, lol

from .._fpc_utils import FPCNotificationsBase
from ._models import LoLFPCMatchToEdit, LoLFPCMatchToSend

if TYPE_CHECKING:
    from bot import AluBot

    class LivePlayerAccountRow(TypedDict):
        summoner_id: str
        player_id: int
        game_name: str
        tag_line: str
        platform: str
        display_name: str
        twitch_id: int
        last_edited: int

    class FindMatchesToEditQueryRow(TypedDict):
        match_id: int
        champion_id: int
        platform: lol.LiteralPlatform
        channel_message_tuples: list[tuple[int, int]]

    class EditLolNotificationQueryRow(TypedDict):
        message_id: int
        channel_id: int
        champion_id: int


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class LoLFPCNotifications(FPCNotificationsBase):
    def __init__(self, bot: AluBot, *args, **kwargs):
        super().__init__(bot, prefix='lol', *args, **kwargs)
        self.notification_matches: list[LoLFPCMatchToSend] = []
        self.live_match_ids: list[int] = []

    async def cog_load(self) -> None:
        self.lol_fpc_notifications_task.add_exception_type(asyncpg.InternalServerError)
        self.lol_fpc_notifications_task.clear_exception_types()
        self.lol_fpc_notifications_task.start()
        return await super().cog_load()

    async def cog_unload(self) -> None:
        self.lol_fpc_notifications_task.stop()  # .cancel()
        return await super().cog_unload()

    async def fill_notification_matches(self):
        self.notification_matches = []
        self.live_match_ids = []

        query = "SELECT DISTINCT character_id FROM lol_favourite_characters"
        favourite_champion_ids = [r for r, in await self.bot.pool.fetch(query)]  # row.unnest

        query = "SELECT DISTINCT player_id FROM lol_favourite_players"
        favourite_player_ids = [r for r, in await self.bot.pool.fetch(query)]
        live_twitch_ids = await self.get_twitch_live_player_ids(const.Twitch.lol_game_category_id, favourite_player_ids)

        query = """
            SELECT a.summoner_id, a.player_id, game_name, tag_line, platform, display_name, twitch_id, last_edited
            FROM lol_accounts a
            JOIN lol_players p
            ON a.player_id = p.player_id
            WHERE p.player_id=ANY($1)
        """
        rows: list[LivePlayerAccountRow] = await self.bot.pool.fetch(query, live_twitch_ids)

        for row in rows:
            try:
                game = await self.bot.riot_api_client.get_lol_spectator_v4_active_game_by_summoner(
                    summoner_id=row["summoner_id"],
                    region=row["platform"],
                )
            except aiohttp.ClientResponseError as exc:
                # we have to do try/except because discord.ext.tasks has aiohttp errors as
                # _valid_exceptions which means it just restarts the loop instead of raising the error
                # and pulsefire unfortunately raises aiohttp errors.
                # I do not to remove them from valid_exceptions.
                if exc.status == 404:
                    log.debug(
                        "%s is not in the active game on account %s#%s",
                        row["display_name"],
                        row["game_name"],
                        row["tag_line"],
                    )
                else:
                    error_embed = (
                        discord.Embed(colour=const.Colour.error())
                        .add_field(
                            name="`lol_spectator_v4_active_game_by_summoner` Error",
                            value=f"Status: {exc.status}",
                        )
                        .add_field(
                            name="Account",
                            value=f"{row['game_name']}#{row['tag_line']} {row['platform']} {row['display_name']}",
                        )
                        .set_footer(text="fill_live_matches in league notifications")
                    )
                    await self.hideout.spam.send(embed=error_embed)
                continue

            # continue game analysis
            if game["gameQueueConfigId"] != const.League.SOLO_RANKED_5v5_QUEUE_ENUM:
                continue

            self.live_match_ids.append(game["gameId"])

            player = next((p for p in game["participants"] if p["summonerId"] == row["summoner_id"]), None)

            if player and player["championId"] in favourite_champion_ids and row["last_edited"] != game["gameId"]:
                query = """
                    SELECT s.channel_id, s.spoil
                    FROM lol_favourite_characters c
                    JOIN lol_favourite_players p on c.guild_id = p.guild_id
                    JOIN lol_settings s on s.guild_id = c.guild_id
                    WHERE character_id=$1 
                        AND player_id=$2
                        AND NOT channel_id=ANY(SELECT channel_id FROM lol_messages WHERE match_id=$3);  
                        AND s.enabled = TRUE   
                """
                channel_spoil_tuples: list[tuple[int, bool]] = [
                    (channel_id, spoil)
                    for channel_id, spoil in await self.bot.pool.fetch(
                        query, player["championId"], row["player_id"], game["gameId"]
                    )
                ]
                if channel_spoil_tuples:
                    log.debug(
                        "Notif %s - %s",
                        row["display_name"],
                        await self.bot.cdragon.champion.name_by_id(player["championId"]),
                    )
                    match_to_send = LoLFPCMatchToSend(
                        match_id=game["gameId"],
                        platform=game["platformId"],  # type: ignore # pulsefire has it as a simple str
                        game_name=row["game_name"],
                        # TODO: ^^^would be cool to get it from game object but currently it's not there.
                        tag_line=row["tag_line"],
                        start_time=game["gameStartTime"],
                        champion_id=player["championId"],
                        all_champion_ids=[p["championId"] for p in game["participants"]],
                        twitch_id=row["twitch_id"],
                        summoner_spell_ids=(player["spell1Id"], player["spell2Id"]),
                        rune_ids=player["perks"]["perkIds"],  # type: ignore # not required key, wtf ?
                        summoner_id=player["summonerId"],
                    )
                    await self.send_notifications(match_to_send, channel_spoil_tuples)

    @aluloop(seconds=59)
    async def lol_fpc_notifications_task(self):
        log.debug(f"--- LoL FPC Notifications Task is starting now ---")
        await self.fill_notification_matches()
        await self.edit_lol_notification_messages()
        log.debug(f"--- LoL FPC Notifications Task is finished ---")

    # POST MATCH EDITS

    async def edit_lol_notification_messages(self):
        query = """
            SELECT match_id, champion_id, platform, ARRAY_AGG ((message_id, channel_id)) channel_message_tuples
            FROM lol_messages
            WHERE NOT match_id=ANY($1)
            GROUP BY match_id, champion_id, platform
            """
        match_rows: list[FindMatchesToEditQueryRow] = await self.bot.pool.fetch(query, self.live_match_ids)

        for match_row in match_rows:
            try:
                match_id = f"{match_row['platform'].upper()}_{match_row['match_id']}"
                continent = lol.PLATFORM_TO_CONTINENT[match_row["platform"]]

                match = await self.bot.riot_api_client.get_lol_match_v5_match(id=match_id, region=continent)
                timeline = await self.bot.riot_api_client.get_lol_match_v5_match_timeline(id=match_id, region=continent)

            except aiohttp.ClientResponseError as exc:
                if exc.status == 404:
                    continue
                else:
                    raise

            for participant in match["info"]["participants"]:
                if participant["championId"] == match_row["champion_id"]:
                    # found our participant
                    match_to_edit = LoLFPCMatchToEdit(self.bot, participant=participant, timeline=timeline)
                    await self.edit_notifications(match_to_edit, match_row["channel_message_tuples"])
            query = "DELETE FROM lol_messages WHERE match_id=$1"
            await self.bot.pool.fetch(query, match_row["match_id"])


async def setup(bot: AluBot):
    await bot.add_cog(LoLFPCNotifications(bot))
