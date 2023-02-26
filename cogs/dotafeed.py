from __future__ import annotations

import datetime
import logging
import time
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Union

import discord
import vdf
from discord import app_commands
from discord.ext import commands, tasks
from steam.core.msg import MsgProto
from steam.enums import emsg
from steam.steamid import EType, SteamID

from .dota import hero
from .dota.const import DOTA_LOGO
from .dota.models import ActiveMatch, OpendotaRequestMatch, PostMatchPlayerData
from .utils.checks import is_manager
from .utils.fpc import FPCBase, TwitchAccCheckCog
from .utils.var import MP, Cid, Clr, Ems, Uid

if TYPE_CHECKING:
    from .utils.bot import AluBot
    from .utils.context import Context

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class DotaFeed(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
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
        self.dota_feed.start()

    @commands.Cog.listener()
    async def on_my_top_games_response(self):
        log.debug("double u tea ef ef")

    async def cog_unload(self) -> None:
        self.dota_feed.cancel()

    async def preliminary_queries(self):
        async def get_all_fav_ids(column_name: str) -> List[int]:
            query = f"SELECT DISTINCT(unnest({column_name})) FROM guilds"
            rows = await self.bot.pool.fetch(query)
            return [row.unnest for row in rows]

        self.hero_fav_ids = await get_all_fav_ids("dotafeed_hero_ids")
        self.player_fav_ids = await get_all_fav_ids("dotafeed_stream_ids")

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
        # also idea with asyncio.Event() or checkin if top_source_dict is populated

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

                query = """ SELECT dotafeed_ch_id
                            FROM guilds
                            WHERE $1=ANY(dotafeed_hero_ids)
                                AND $2=ANY(dotafeed_stream_ids)
                                AND NOT dotafeed_ch_id=ANY(
                                    SELECT channel_id FROM dota_messages WHERE match_id=$3
                                )          
                        """
                channel_ids = [i for i, in await self.bot.pool.fetch(query, person.hero_id, user.id, match.match_id)]
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

            em, img_file = await match.notif_embed_and_file(self.bot)
            log.debug("LF | Successfully made embed+file")
            em.title = f"{ch.guild.owner.name}'s fav hero + player spotted"
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


class PostMatchEdits(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
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
    async def opendota_ratelimit(self, ctx: Context):
        """Send opendota rate limit numbers"""
        e = discord.Embed(colour=Clr.prpl, description=f"Odota limits: {self.bot.odota_ratelimit}")
        await ctx.reply(embed=e)

    @tasks.loop(time=datetime.time(hour=2, minute=51, tzinfo=datetime.timezone.utc))
    async def daily_report(self):
        e = discord.Embed(title="Daily Report", colour=MP.black())
        the_dict = self.bot.odota_ratelimit
        month, minute = int(the_dict['monthly']), int(the_dict['minutely'])
        e.description = f"Odota limits. monthly: {month} minutely: {minute}"
        content = f'<@{Uid.alu}>' if month < 10_000 else ''
        await self.bot.get_channel(Cid.daily_report).send(content=content, embed=e)  # type: ignore

    @daily_report.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


class AddDotaPlayerFlags(commands.FlagConverter, case_insensitive=True):
    name: str
    steam: str
    twitch: bool


class RemoveStreamFlags(commands.FlagConverter, case_insensitive=True):
    name: Optional[str]
    steam: Optional[str]


class DotaFeedToolsCog(commands.Cog, FPCBase, name="Dota 2"):
    """Commands to set up fav hero + player notifs.

    These commands allow you to choose players from our database as your favorite \
    (or you can request adding them if missing) and choose your favorite Dota 2 heroes. \
    The bot will send messages in a chosen channel when your fav player picks your fav hero.

    **Tutorial**
    1. Set channel with
    `$dota channel set #channel`
    2. Add players to your favourites, i.e.
    `$dota player add gorgc, bzm`
    List of available players can be seen with `$dota database list`
    3. Request missing players to the database , i.e.
    `/dota database request name: cr1tdota steam: 76561197986172872 twitch: yes`
    4. Add heroes to your favourites, i.e.
    `/dota hero add name1: Dark Willow name2: Mirana name3: Anti-Mage`
    5. Use `remove` counterpart commands to `add` to edit out player/hero lists
    *Pro-Tip.* Use autocomplete
    6. Ready ! More info below
    """

    def __init__(self, bot: AluBot):
        super().__init__(
            feature_name="DotaFeed",
            game_name="Dota 2",
            game_codeword="dota",
            game_logo=DOTA_LOGO,
            colour=Clr.prpl,
            bot=bot,
            players_table="dota_players",
            accounts_table="dota_accounts",
            channel_id_column="dotafeed_ch_id",
            players_column="dotafeed_stream_ids",
            characters_column="dotafeed_hero_ids",
            spoil_column="dotafeed_spoils_on",
            acc_info_columns=["friend_id"],
            get_char_id_by_name=hero.id_by_name,
            get_char_name_by_id=hero.name_by_id,
            get_all_character_names=hero.get_all_hero_names,
            character_gather_word="heroes",
        )
        self.bot: AluBot = bot

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(Ems.DankLove)

    async def cog_load(self) -> None:
        await self.bot.ini_twitch()

    # dota ##############################################

    slh_dota = app_commands.Group(
        name="dota",
        description="Group command about DotaFeed",
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @is_manager()
    @commands.group(name="dota")
    async def ext_dota(self, ctx: Context):
        """Group command about Dota, for actual commands use it together with subcommands"""
        await ctx.scnf()

    # dota channel ######################################

    slh_dota_channel = app_commands.Group(
        name="channel",
        description="Group command about DotaFeed channel settings",
        parent=slh_dota,
    )

    @is_manager()
    @ext_dota.group(name="channel")
    async def ext_dota_channel(self, ctx: Context):
        """Group command about DotaFeed Channel, for actual commands use it together with subcommands"""
        await ctx.scnf()

    # dota channel set ##################################

    @slh_dota_channel.command(name="set")
    @app_commands.describe(channel="Choose channel to set up DotaFeed notifications")
    async def slh_dota_channel_set(self, ntr: discord.Interaction[AluBot], channel: Optional[discord.TextChannel]):
        """Set channel to be the DotaFeed notifications channel."""
        await self.channel_set(ntr, channel)

    @is_manager()
    @ext_dota_channel.command(name="set", usage="[channel=curr]")
    async def ext_dota_channel_set(self, ctx: Context, channel: Optional[discord.TextChannel]):
        """Set channel to be the DotaFeed notifications channel."""
        await self.channel_set(ctx, channel)

    # dota channel disable ##################################

    @slh_dota_channel.command(name="disable", description="Disable DotaFeed notifications channel")
    async def slh_dota_channel_disable(self, ntr: discord.Interaction[AluBot]):
        """Disable DotaFeed notifications channel. Data won't be affected."""
        await self.channel_disable(ntr)

    @is_manager()
    @ext_dota_channel.command(name="disable")
    async def ext_dota_channel_disable(self, ctx: Context):
        """Stop getting DotaFeed notifs. Data about fav heroes/players won't be affected."""
        await self.channel_disable(ctx)

    # dota channel check ##################################

    @slh_dota_channel.command(name="check", description="Check if DotaFeed channel is set up")
    async def slh_dota_channel_check(self, ntr: discord.Interaction[AluBot]):
        """Check if DotaFeed channel is set up"""
        await self.channel_check(ntr)

    @is_manager()
    @ext_dota_channel.command(name="check")
    async def ext_dota_channel_check(self, ctx: Context):
        """Check if DotaFeed channel is set up in the server."""
        await self.channel_check(ctx)

    # dota database ##################################

    slh_dota_database = app_commands.Group(
        name="database",
        description="Group command about DotaFeed database",
        parent=slh_dota,
    )

    @is_manager()
    @ext_dota.group(name="database", aliases=["db"])
    async def ext_dota_database(self, ctx: Context):
        """Group command about Dota 2 database, for actual commands use it together with subcommands"""
        await ctx.scnf()

    # helper functions ##################################

    @staticmethod
    def cmd_usage_str(**kwargs):
        friend_id = kwargs.pop("friend_id")
        twitch = bool(kwargs.pop("twitch_id"))
        return f"steam: {friend_id} twitch: {twitch}"

    @staticmethod
    def player_acc_string(**kwargs):
        steam_id = kwargs.pop("id")
        friend_id = kwargs.pop("friend_id")
        return (
            f"`{steam_id}` - `{friend_id}`| "
            f"[Steam](https://steamcommunity.com/profiles/{steam_id})"
            f"/[Dotabuff](https://www.dotabuff.com/players/{friend_id})"
        )

    @staticmethod
    def get_steam_id_and_64(steam_string: str):
        steam_acc = SteamID(steam_string)
        if steam_acc.type != EType.Individual:
            steam_acc = SteamID.from_url(steam_string)  # type: ignore # ValvePython does not care much about TypeHints

        if steam_acc is None or (hasattr(steam_acc, "type") and steam_acc.type != EType.Individual):
            raise commands.BadArgument(
                "Error checking steam profile for {steam}.\n"
                "Check if your `steam` flag is correct steam id in either 64/32/3/2/friend_id representations "
                "or just give steam profile link to the bot."
            )
        return steam_acc.as_64, steam_acc.id

    async def get_account_dict(self, *, steam_flag: str) -> dict:
        steam_id, friend_id = self.get_steam_id_and_64(steam_flag)
        return {"id": steam_id, "friend_id": friend_id}

    # dota database list ##################################

    @slh_dota_database.command(
        name="list", description="List of players in the database available for DotaFeed feature"
    )
    async def slh_dota_database_list(self, ntr: discord.Interaction[AluBot]):
        """List of players in the database available for DotaFeed feature."""
        await self.database_list(ntr)

    @is_manager()
    @ext_dota_database.command(name="list")
    async def ext_dota_database_list(self, ctx: Context):
        """List of players in the database available for DotaFeed feature."""
        await self.database_list(ctx)

    # dota database request ##################################

    @slh_dota_database.command(name="request")
    async def dota_database_request(self, ntr: discord.Interaction[AluBot], name: str, steam: str, twitch: bool):
        """Request player to be added into the database.

        Parameters
        ----------
        ntr: discord.Interaction
        name:
            Player name. If it is a twitch tv streamer then provide their twitch handle.
        steam:
            Steamid in any of 64/32/3/2 versions, friend_id or just steam profile link.
        twitch:
            If you proved twitch handle for "name" then press `True` otherwise `False`.
        """

        player_dict = await self.get_player_dict(name_flag=name, twitch_flag=twitch)
        account_dict = await self.get_account_dict(steam_flag=steam)
        await self.database_request(ntr, player_dict, account_dict)

    @is_manager()
    @ext_dota_database.command(
        name="request",
        usage="name: <name> steam: <steamid> twitch: <yes/no>",
    )
    async def ext_dota_database_request(self, ctx: Context, *, flags: AddDotaPlayerFlags):
        """Request player to be added into the database.
        This will send a request message into Aluerie's personal logs channel.
        """
        player_dict = await self.get_player_dict(name_flag=flags.name, twitch_flag=flags.twitch)
        account_dict = await self.get_account_dict(steam_flag=flags.steam)
        await self.database_request(ctx, player_dict, account_dict)

    # dota player ##################################

    slh_dota_player = app_commands.Group(
        name="player",
        description="Group command about DotaFeed player",
        parent=slh_dota,
    )

    @is_manager()
    @ext_dota.group(name="player", aliases=["streamer"])
    async def ext_dota_player(self, ctx: Context):
        """Group command about Dota 2 player, for actual commands use it together with subcommands"""
        await ctx.scnf()

    # dota player add ##################################

    async def player_add_autocomplete(self, ntr: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        return await self.player_add_remove_autocomplete(ntr, current, mode_add=True)

    @slh_dota_player.command(name="add")
    @app_commands.describe(
        **{
            f"name{i}": "Name of a player. Suggestions from database above exclude your already fav players"
            for i in range(1, 11)
        }
    )
    @app_commands.autocomplete(
        name1=player_add_autocomplete,
        name2=player_add_autocomplete,
        name3=player_add_autocomplete,
        name4=player_add_autocomplete,
        name5=player_add_autocomplete,
        name6=player_add_autocomplete,
        name7=player_add_autocomplete,
        name8=player_add_autocomplete,
        name9=player_add_autocomplete,
        name10=player_add_autocomplete,
    )
    # @app_commands.autocomplete(**{f'name{i}': player_add_autocomplete for i in range(1, 11)})
    async def slh_dota_player_add(
        self,
        ntr: discord.Interaction[AluBot],
        name1: Optional[str],
        name2: Optional[str],
        name3: Optional[str],
        name4: Optional[str],
        name5: Optional[str],
        name6: Optional[str],
        name7: Optional[str],
        name8: Optional[str],
        name9: Optional[str],
        name10: Optional[str],
    ):
        """Add player to your favourites."""
        await self.player_add_remove(ntr, locals(), mode_add=True)

    @is_manager()
    @ext_dota_player.command(name="add", usage="<player_name(-s)>")
    async def ext_dota_player_add(self, ctx: Context, *, player_names: str):
        """Add player to your favourites."""
        await self.player_add_remove(ctx, locals(), mode_add=True)

    # dota player remove ##################################

    async def player_remove_autocomplete(
        self, ntr: discord.Interaction[AluBot], current: str
    ) -> List[app_commands.Choice[str]]:
        return await self.player_add_remove_autocomplete(ntr, current, mode_add=False)

    @slh_dota_player.command(name="remove")
    @app_commands.describe(**{f"name{i}": "Name of a player" for i in range(1, 11)})
    @app_commands.autocomplete(
        name1=player_remove_autocomplete,
        name2=player_remove_autocomplete,
        name3=player_remove_autocomplete,
        name4=player_remove_autocomplete,
        name5=player_remove_autocomplete,
        name6=player_remove_autocomplete,
        name7=player_remove_autocomplete,
        name8=player_remove_autocomplete,
        name9=player_remove_autocomplete,
        name10=player_remove_autocomplete,
    )
    # @app_commands.autocomplete(**{f'name{i}': player_remove_autocomplete for i in range(1, 11)})
    async def slh_dota_player_remove(
        self,
        ntr: discord.Interaction[AluBot],
        name1: Optional[str],
        name2: Optional[str],
        name3: Optional[str],
        name4: Optional[str],
        name5: Optional[str],
        name6: Optional[str],
        name7: Optional[str],
        name8: Optional[str],
        name9: Optional[str],
        name10: Optional[str],
    ):
        """Remove player from your favourites."""
        await self.player_add_remove(ntr, locals(), mode_add=False)

    @is_manager()
    @ext_dota_player.command(name="remove", usage="<player_name(-s)>")
    async def ext_dota_player_remove(self, ctx: Context, *, player_names: str):
        """Remove player from your favourites."""
        await self.player_add_remove(ctx, locals(), mode_add=False)

    # dota player list ##################################

    @slh_dota_player.command(name="list")
    async def slh_dota_player_list(self, ntr: discord.Interaction[AluBot]):
        """Show list of your favourite players."""
        await self.player_list(ntr)

    @is_manager()
    @ext_dota_player.command(name="list")
    async def ext_dota_player_list(self, ctx: Context):
        """Show current list of fav players."""
        await self.player_list(ctx)

    # dota hero ##################################

    slh_dota_hero = app_commands.Group(
        name="hero",
        description="Group command about DotaFeed hero",
        parent=slh_dota,
    )

    @is_manager()
    @ext_dota.group(name="hero")
    async def ext_dota_hero(self, ctx: Context):
        """Group command about Dota 2, for actual commands use it together with subcommands"""
        await ctx.scnf()

    # dota hero add ##################################

    async def hero_add_autocomplete(self, ntr: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        return await self.character_add_remove_autocomplete(ntr, current, mode_add=True)

    @slh_dota_hero.command(name="add")
    @app_commands.describe(**{f"name{i}": "Name of a hero" for i in range(1, 11)})
    @app_commands.autocomplete(
        name1=hero_add_autocomplete,
        name2=hero_add_autocomplete,
        name3=hero_add_autocomplete,
        name4=hero_add_autocomplete,
        name5=hero_add_autocomplete,
        name6=hero_add_autocomplete,
        name7=hero_add_autocomplete,
        name8=hero_add_autocomplete,
        name9=hero_add_autocomplete,
        name10=hero_add_autocomplete,
    )
    # @app_commands.autocomplete(**{f'name{i}': hero_add_autocomplete for i in range(1, 11)})
    async def slh_dota_hero_add(
        self,
        ntr: discord.Interaction[AluBot],
        name1: Optional[str],
        name2: Optional[str],
        name3: Optional[str],
        name4: Optional[str],
        name5: Optional[str],
        name6: Optional[str],
        name7: Optional[str],
        name8: Optional[str],
        name9: Optional[str],
        name10: Optional[str],
    ):
        """Add hero to your favourites."""
        await self.character_add_remove(ntr, locals(), mode_add=True)

    @is_manager()
    @ext_dota_hero.command(name="add", usage="<hero_name(-s)>")
    async def ext_dota_hero_add(self, ctx: Context, *, hero_names: str):
        """Add hero(-es) to your fav heroes list. \
        Use names from Dota 2 hero grid. For example,
        • `Anti-Mage` (letter case does not matter) and not `Magina`;
        • `Queen of Pain` and not `QoP`.
        """
        # At last, you can find proper name
        # [here](https://api.opendota.com/api/constants/heroes) with Ctrl+F \
        # under one of `"localized_name"`
        await self.character_add_remove(ctx, locals(), mode_add=True)

    # dota hero remove ##################################

    async def hero_remove_autocomplete(self, ntr: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        return await self.character_add_remove_autocomplete(ntr, current, mode_add=False)

    @slh_dota_hero.command(name="remove")
    @app_commands.describe(**{f"name{i}": "Name of a hero" for i in range(1, 11)})
    @app_commands.autocomplete(
        name1=hero_remove_autocomplete,
        name2=hero_remove_autocomplete,
        name3=hero_remove_autocomplete,
        name4=hero_remove_autocomplete,
        name5=hero_remove_autocomplete,
        name6=hero_remove_autocomplete,
        name7=hero_remove_autocomplete,
        name8=hero_remove_autocomplete,
        name9=hero_remove_autocomplete,
        name10=hero_remove_autocomplete,
    )
    # @app_commands.autocomplete(**{f'name{i}': hero_add_autocomplete for i in range(1, 11)})
    async def slh_dota_hero_remove(
        self,
        ntr: discord.Interaction[AluBot],
        name1: Optional[str],
        name2: Optional[str],
        name3: Optional[str],
        name4: Optional[str],
        name5: Optional[str],
        name6: Optional[str],
        name7: Optional[str],
        name8: Optional[str],
        name9: Optional[str],
        name10: Optional[str],
    ):
        """Remove hero from your favourites."""
        await self.character_add_remove(ntr, locals(), mode_add=False)

    @is_manager()
    @ext_dota_hero.command(name="remove", usage="<hero_name(-s)>")
    async def ext_dota_hero_remove(self, ctx: Context, *, hero_names: str):
        """Remove hero(-es) from your fav heroes list."""
        await self.character_add_remove(ctx, locals(), mode_add=False)

    # dota hero list ##################################

    @slh_dota_hero.command(name="list")
    async def slh_dota_hero_list(self, ntr: discord.Interaction[AluBot]):
        """Show your favourite heroes list."""
        await self.character_list(ntr)

    @is_manager()
    @ext_dota_hero.command(name="list")
    async def ext_dota_hero_list(self, ctx: Context):
        """Show current list of fav heroes."""
        await self.character_list(ctx)

    # dota spoil ##################################

    @slh_dota.command(name="spoil")
    @app_commands.describe(spoil="`True` to enable spoiling with stats, `False` for disable")
    async def slh_dota_spoil(self, ntr: discord.Interaction[AluBot], spoil: bool):
        """Turn on/off spoiling resulting stats for matches."""
        await self.spoil(ntr, spoil)

    @is_manager()
    @ext_dota.command(name="spoil")
    async def ext_dota_spoil(self, ctx: Context, spoil: bool):
        """Turn on/off spoiling resulting stats for matches.
        It is "on" by default, so it can show what items players finished with and KDA.
        """
        await self.spoil(ctx, spoil)


async def setup(bot: AluBot):
    await bot.add_cog(DotaFeed(bot))
    await bot.add_cog(PostMatchEdits(bot))
    await bot.add_cog(DotaFeedToolsCog(bot))
    await bot.add_cog(TwitchAccCheckCog(bot, "dota_players", 16))
