from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Mapping, NamedTuple

import aiohttp
import asyncpg
import discord

from utils import aluloop, const, lol
from utils.lol.const import platform_to_region

from .._base import FPCCog
from ._models import LoLNotificationMatch

if TYPE_CHECKING:
    from bot import AluBot

    class LiveAccountRow(NamedTuple):  # TODO: proper asyncpg typing
        id: str
        account_name: str
        platform: str
        display_name: str
        lower_name: str
        twitch_id: int
        last_edited: int

    class LoLMatchRecord(NamedTuple):
        match_id: int
        platform: str
        region: str
        is_finished: bool


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)  # todo: change to info


class LoLFPCNotifications(FPCCog):
    def __init__(self, bot: AluBot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.notification_matches: list[LoLNotificationMatch] = []
        self.live_match_ids: list[int] = []

    async def cog_load(self) -> None:
        self.lol_fpc_notifications_task.add_exception_type(asyncpg.InternalServerError)
        self.lol_fpc_notifications_task.start()
        return await super().cog_load()

    async def cog_unload(self) -> None:
        self.lol_fpc_notifications_task.stop()  # .cancel()
        return await super().cog_unload()

    async def get_live_lol_player_lower_names(self) -> list[str]:
        """Get `lower_name` for favourite League of Legends streams that are currently live."""
        query = """ SELECT twitch_id, lower_name
                    FROM lol_players
                    WHERE lower_name=ANY(SELECT DISTINCT lower_name FROM lol_favourite_players)
                """
        twitch_id_to_lower_name: Mapping[int, str] = {
            r.twitch_id: r.lower_name for r in await self.bot.pool.fetch(query)
        }
        if not twitch_id_to_lower_name:
            # otherwise fetch_streams fetches top100 streams and we dont want that.
            return []

        live_twitch_ids = [
            i.user.id
            for i in await self.bot.twitch.fetch_streams(user_ids=list(twitch_id_to_lower_name.keys()))
            if i.game_id == const.Twitch.lol_game_category_id
        ]
        return [twitch_id_to_lower_name[i] for i in live_twitch_ids]

    async def fill_notification_matches(self):
        self.notification_matches = []
        self.live_match_ids = []

        query = "SELECT DISTINCT character_id FROM lol_favourite_characters"
        favourite_champion_ids = [r for r, in await self.bot.pool.fetch(query)]  # row.unnest

        live_lower_names = await self.get_live_lol_player_lower_names()

        query = """ SELECT a.id, account_name, platform, display_name, p.lower_name, twitch_id, last_edited
                    FROM lol_accounts a
                    JOIN lol_players p
                    ON a.lower_name = p.lower_name
                    WHERE p.lower_name=ANY($1)
                """
        rows: list[LiveAccountRow] = await self.bot.pool.fetch(query, live_lower_names)
        async with self.bot.riot_api_client as riot_api_client:
            for r in rows:
                log.debug("%s", r)
                try:
                    game = await riot_api_client.get_lol_spectator_v4_active_game_by_summoner(
                        summoner_id=r.id,
                        region=r.platform,  # todo: region = platform xd
                    )
                except aiohttp.ClientResponseError as exc:
                    # we have to do try/except because discord.ext.tasks has aiohttp errors as
                    # _valid_exceptions which means it just restarts the loop instead of raising the error
                    # and pulsefire unfortunately raises aiohttp errors.
                    # I do not to remove them from valid_exceptions.
                    if exc.status == 404:
                        log.debug("Player %s is not in the active game on account %s", r.display_name, r.account_name)
                    else:
                        e = discord.Embed(colour=const.Colour.error())
                        e.add_field(
                            name="`lol_spectator_v4_active_game_by_summoner` Error", value=f"Status: {exc.status}"
                        )
                        e.add_field(name="Account", value=f"{r.account_name} {r.platform} {r.display_name}")
                        e.set_footer(text="fill_live_matches in league notifications")
                        await self.hideout.spam.send(embed=e)
                    continue

                log.debug("%s", game["gameId"])

                # continue game analysis
                if not game["gameQueueConfigId"] != const.League.SOLO_RANKED_5v5_QUEUE_ENUM:
                    continue

                self.live_match_ids.append(game["gameId"])

                player = next((x for x in game["participants"] if x["summonerId"] == r.id), None)

                if player and player["championId"] in favourite_champion_ids and r.last_edited != game["gameId"]:
                    query = """ SELECT ls.channel_id 
                                FROM lol_favourite_characters c
                                JOIN lol_favourite_players p on c.guild_id = p.guild_id
                                JOIN lol_settings s on s.guild_id = c.guild_id
                                WHERE character_id=$1 AND lower_name=$2
                                AND NOT channel_id=ANY(SELECT channel_id FROM lol_messages WHERE match_id=$3);     
                            """
                    channel_id_rows = await self.bot.pool.fetch(
                        query, player["championId"], r.lower_name, game["gameId"]
                    )
                    channel_ids = [channel_id for channel_id, in channel_id_rows]
                    if channel_ids:
                        log.debug("Notif %s - %s", r.display_name, await lol.champion.key_by_id(player["championId"]))
                        self.notification_matches.append(
                            LoLNotificationMatch(
                                match_id=game["gameId"],
                                platform=game["platformId"],  # type: ignore # pulsefire has it as a simple str
                                account_name=player["summonerName"],  # todo: what does it show now?
                                start_time=game["gameStartTime"],
                                champion_id=player["championId"],
                                all_champion_ids=[p["championId"] for p in game["participants"]],
                                twitch_id=r.twitch_id,
                                summoner_spell_ids=(player["spell1Id"], player["spell2Id"]),
                                rune_ids=player["perks"]["perkIds"],
                                channel_ids=channel_ids,
                                summoner_id=player["summonerId"],
                            )
                        )

    async def send_notifications(self, match: LoLNotificationMatch):
        log.debug("Sending LoL FPC Notifications")
        for channel_id in match.channel_ids:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                log.debug("The LoL FPC Notification channel %s is None", channel_id)
                # todo: we need to do something in this case like clear it from cache? maybe on more fails?
                continue

            embed, image_file = await match.get_embed_and_file(self.bot)
            log.debug("Successfully made embed + image file")
            assert isinstance(channel, discord.TextChannel)

            owner_name = channel.guild.owner.display_name if channel.guild.owner else "Somebody"
            embed.title = f"{owner_name}'s fav champ + player spotted"
            msg = await channel.send(embed=embed, file=image_file)

            query = """ INSERT INTO lol_matches (match_id, region, platform)
                        VALUES ($1, $2, $3)
                        ON CONFLICT DO NOTHING 
                    """
            await self.bot.pool.execute(query, match.match_id, platform_to_region(match.platform), match.platform)
            query = """ INSERT INTO lol_messages
                        (message_id, channel_id, match_id, champ_id) 
                        VALUES ($1, $2, $3, $4)
                    """
            await self.bot.pool.execute(query, msg.id, channel.id, match.match_id, match.champion_id)
            query = "UPDATE lol_accounts SET last_edited=$1 WHERE id=$2"
            await self.bot.pool.execute(query, match.match_id, match.summoner_id)

    async def declare_matches_finished(self):
        query = """ SELECT * FROM lol_matches
                    WHERE NOT match_id=ANY($1)
                """
        rows: list[LoLMatchRecord] = await self.bot.pool.fetch(query, self.live_match_ids)
        self.bot.dispatch("lol_fpc_notification_match_finished", rows)

    @aluloop(seconds=59)
    async def lol_fpc_notifications_task(self):
        log.debug(f"--- LoL FPC Notifications Task is starting now ---")
        await self.fill_notification_matches()
        for match in self.notification_matches:
            await self.send_notifications(match)
        await self.declare_matches_finished()
        log.debug(f"--- LoL FPC Notifications Task is finished ---")


async def setup(bot: AluBot):
    await bot.add_cog(LoLFPCNotifications(bot))
