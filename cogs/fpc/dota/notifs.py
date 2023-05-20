from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Dict, List, Set, Union

import asyncpg
import discord
import vdf
from discord.ext import commands, tasks
from steam.core.msg import MsgProto
from steam.enums import emsg

from utils import AluCog
from utils.dota import hero

from ._models import ActiveMatch

if TYPE_CHECKING:
    from utils import AluBot

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class DotaNotifs(AluCog):
    def __init__(self, bot: AluBot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.lobby_ids: Set[int] = set()
        self.top_source_dict: Dict = {}
        self.live_matches: List[ActiveMatch] = []
        self.hero_fav_ids: List[int] = []
        self.player_fav_ids: List[int] = []

    async def cog_load(self) -> None:
        await self.bot.ini_twitch()
        self.bot.ini_steam_dota()

        @self.bot.dota.on("top_source_tv_games")  # type: ignore
        def response(result):
            # log.debug(
            #     f"DF | top_source_tv_games resp ng: {result.num_games} sg: {result.specific_games} "
            #     f"{result.start_game, result.game_list_index, len(result.game_list)} "
            #     f"{result.game_list[0].players[0].account_id}"
            # )
            for match in result.game_list:
                self.top_source_dict[match.match_id] = match
            # not good: we have 10+ top_source_tv_events, but we send response on the very first one so it s not precise
            self.bot.dota.emit("my_top_games_response")
            # did not work
            # self.bot.dispatch('my_top_games_response')

        # self.bot.dota.on('top_source_tv_games', response)

        # maybe asyncpg.PostgresConnectionError
        self.dota_feed.add_exception_type(asyncpg.InternalServerError)
        self.dota_feed.start()
        return await super().cog_load()

    @commands.Cog.listener()
    async def on_my_top_games_response(self):
        log.debug("double u tea ef ef")

    async def cog_unload(self) -> None:
        self.dota_feed.cancel()
        return await super().cog_unload()

    async def preliminary_queries(self):
        async def get_all_fav_ids(table_name: str, column_name: str) -> List[int]:
            query = f"DISTINCT(SELECT {column_name} FROM dota_favourite_{table_name})"
            rows = await self.bot.pool.fetch(query)
            return [r for r, in rows]

        self.hero_fav_ids = await get_all_fav_ids("characters", 'character_id')
        self.player_fav_ids = await get_all_fav_ids("players", 'player_name')

    async def get_args_for_top_source(self, specific_games_flag: bool) -> Union[None, dict]:
        self.bot.steam_dota_login()

        if specific_games_flag:
            proto_msg = MsgProto(emsg.EMsg.ClientRichPresenceRequest)
            proto_msg.header.routing_appid = 570  # type: ignore

            query = "SELECT id FROM dota_accounts WHERE player_id=ANY($1)"
            steam_ids = [i for i, in await self.bot.pool.fetch(query, self.player_fav_ids)]
            proto_msg.body.steamid_request.extend(steam_ids)  # type: ignore
            resp = self.bot.steam.send_message_and_wait(proto_msg, emsg.EMsg.ClientRichPresenceInfo, timeout=8)
            if resp is None:
                log.warning("resp is None, hopefully everything else will be fine tho;")
                return None

            # print(resp)

            async def get_lobby_id_by_rp_kv(rp_bytes):
                rp = vdf.binary_loads(rp_bytes)["RP"]
                # print(rp)
                if lobby_id := int(rp.get("WatchableGameID", 0)):
                    if rp.get("param0", 0) == "#DOTA_lobby_type_name_ranked":
                        if await hero.id_by_npcname(rp.get("param2", "#")[1:]) in self.hero_fav_ids:
                            return lobby_id

            lobby_ids = list(
                dict.fromkeys(
                    [
                        y
                        for x in resp.rich_presence
                        if (x.rich_presence_kv and (y := await get_lobby_id_by_rp_kv(x.rich_presence_kv)) is not None)
                    ]
                )
            )
            if lobby_ids:
                return {"lobby_ids": lobby_ids}
            else:
                return None
        else:
            return {"start_game": 90}

    def request_top_source(self, args):
        self.bot.dota.request_top_source_tv_games(**args)
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
            our_persons = [x for x in match.players if x.account_id in friend_ids and x.hero_id in self.hero_fav_ids]
            for person in our_persons:
                query = """ SELECT id, display_name, twitch_id 
                            FROM dota_players 
                            WHERE id=(SELECT player_id FROM dota_accounts WHERE friend_id=$1)
                        """
                user = await self.bot.pool.fetchrow(query, person.account_id)

                query = """ SELECT channel_id
                            FROM dota_settings
                            WHERE $1=ANY(characters)
                                AND $2=ANY(players)
                                AND NOT channel_id=ANY(
                                    SELECT channel_id FROM dota_messages WHERE match_id=$3
                                )          
                        """
                channel_ids = [
                    i for i, in await self.bot.pool.fetch(query, person.hero_id, user.id, match.match_id, 'dota')
                ]
                if channel_ids:
                    log.debug(f"DF | {user.display_name} - {await hero.name_by_id(person.hero_id)}")
                    self.live_matches.append(
                        ActiveMatch(
                            match_id=match.match_id,
                            start_time=match.activate_time,
                            player_name=user.display_name,
                            twitchtv_id=user.twitch_id,
                            hero_id=person.hero_id,
                            hero_ids=[x.hero_id for x in match.players],
                            server_steam_id=match.server_steam_id,
                            channel_ids=channel_ids,
                        )
                    )

    async def send_notifications(self, match: ActiveMatch):
        log.debug("DF | Sending LoLFeed notification")
        for ch_id in match.channel_ids:
            if (ch := self.bot.get_channel(ch_id)) is None:
                log.debug("LF | The channel is None")
                continue

            assert isinstance(ch, discord.TextChannel)
            em, img_file = await match.notif_embed_and_file(self.bot)
            log.debug("LF | Successfully made embed+file")
            owner_name = ch.guild.owner.name if ch.guild.owner else 'Somebody'
            em.title = f"{owner_name}'s fav hero + player spotted"
            msg = await ch.send(embed=em, file=img_file)
            query = """ INSERT INTO dota_matches (id) 
                        VALUES ($1) 
                        ON CONFLICT DO NOTHING
                    """
            await self.bot.pool.execute(query, match.match_id)
            query = """ INSERT INTO dota_messages 
                        (message_id, channel_id, match_id, hero_id, twitch_status) 
                        VALUES ($1, $2, $3, $4, $5)
                    """
            await self.bot.pool.execute(query, msg.id, ch.id, match.match_id, match.hero_id, match.twitch_status)

    async def declare_matches_finished(self):
        query = """ UPDATE dota_matches 
                    SET is_finished=TRUE
                    WHERE NOT id=ANY($1)
                    AND dota_matches.is_finished IS DISTINCT FROM TRUE
                """
        await self.bot.pool.execute(query, list(self.top_source_dict.keys()))

    @tasks.loop(seconds=59)
    async def dota_feed(self):
        log.debug(f"DF | --- Task is starting now ---")

        await self.preliminary_queries()
        self.top_source_dict = {}
        for specific_games_flag in [False, True]:
            args = await self.get_args_for_top_source(specific_games_flag)
            if args:  # check args value is not empty
                start_time = time.perf_counter()
                log.debug("DF | calling request_top_source NOW ---")
                self.request_top_source(args)
                # await self.bot.loop.run_in_executor(None, self.request_top_source, args)
                # await asyncio.to_thread(self.request_top_source, args)
                log.debug(f"DF | top source request took {time.perf_counter() - start_time} secs")
        log.debug(f"DF | len top_source_dict = {len(self.top_source_dict)}")
        await self.analyze_top_source_response()
        for match in self.live_matches:
            await self.send_notifications(match)

        await self.declare_matches_finished()
        log.debug(f"DF | --- Task is finished ---")

    @dota_feed.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @dota_feed.error
    async def dotafeed_error(self, error):
        await self.bot.send_traceback(error, where="DotaFeed Notifs")
        # self.dotafeed.restart()


async def setup(bot):
    await bot.add_cog(DotaNotifs(bot))
