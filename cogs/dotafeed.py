from __future__ import annotations

from datetime import datetime, timezone, time
import logging
from typing import TYPE_CHECKING, Optional, List, Literal

import vdf
from discord import Embed, TextChannel, app_commands
from discord.ext import commands, tasks
from steam.core.msg import MsgProto
from steam.enums import emsg
from steam.steamid import SteamID, EType

from .dota.const import ODOTA_API_URL
from .dota.models import PostMatchPlayerData, ActiveMatch

from .utils.checks import is_guild_owner, is_trustee
from .utils.distools import send_traceback
from .dota import hero
from .utils.fpc import FPCBase
from .utils.var import Clr, Ems

if TYPE_CHECKING:
    from discord import Interaction
    from .utils.bot import AluBot
    from .utils.context import Context

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class DotaFeed(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

        # self.dotafeed.start()
        self.lobby_ids = set()
        self.active_matches = []

        self.top_source_dict = {}
        self.matches_to_send = []

        self.hero_fav_ids = []
        self.player_fav_ids = []

    def cog_load(self) -> None:
        self.bot.ini_steam_dota()

        @self.bot.dota.on('top_source_tv_games')
        def response(result):
            # log.debug(
            #    f"top_source_tv_games resp ng: {result.num_games} sg: {result.specific_games} "
            #    f"{result.start_game, result.game_list_index, len(result.game_list)} "
            #    f"{result.game_list[0].players[0].account_id}"
            # )
            for match in result.game_list:
                self.top_source_dict[match.match_id] = match

    def cog_unload(self) -> None:
        self.dotafeed.cancel()

    async def preliminary_queries(self):
        async def get_all_fav_ids(column_name: str):
            query = f'SELECT DISTINCT(unnest({column_name})) FROM guilds'
            rows = await self.bot.pool.fetch(query)
            return [row.unnest for row in rows]

        self.hero_fav_ids = await get_all_fav_ids('dotafeed_hero_ids')
        self.player_fav_ids = await get_all_fav_ids('dotafeed_stream_ids')

    async def get_args_for_top_source(self, specific_games_flag):
        self.bot.steam_dota_login()
        if specific_games_flag:
            proto_msg = MsgProto(emsg.EMsg.ClientRichPresenceRequest)
            proto_msg.header.routing_appid = 570

            query = 'SELECT id FROM dotaaccs WHERE fav_id=ANY($1)'
            rows = await self.bot.pool.fetch(query, self.player_fav_ids)

            steam_ids = [row.id for row in rows]
            proto_msg.body.steamid_request.extend(steam_ids)
            resp = self.bot.steam.send_message_and_wait(proto_msg, emsg.EMsg.ClientRichPresenceInfo, timeout=8)
            if resp is None:
                print('resp is None, hopefully everything else will be fine tho;')
                return
            # print(resp)

            async def get_lobby_id_by_rich_presence_kv(rp_bytes):
                rp = vdf.binary_loads(rp_bytes)['RP']
                # print(rp)
                if lobby_id := int(rp.get('WatchableGameID', 0)):
                    if rp.get('param0', 0) == '#DOTA_lobby_type_name_ranked':
                        if await hero.id_by_npcname(rp.get('param2', '#')[1:]) in self.hero_fav_ids:
                            return lobby_id

            lobby_ids = set(
                await get_lobby_id_by_rich_presence_kv(item.rich_presence_kv)
                for item in resp.rich_presence if item.rich_presence_kv
            )

            return {'lobby_ids': list(lobby_ids)}
        else:
            return {'start_game': 90}

    async def analyze_top_source_response(self):
        query = 'SELECT friendid FROM dotaaccs WHERE fav_id=ANY($1)'
        rows = await self.bot.pool.fetch(query, self.player_fav_ids)
        friend_ids = [row.friendid for row in rows]

        for match in self.top_source_dict.values():
            our_persons = [x for x in match.players if x.account_id in friend_ids and x.hero_id in self.hero_fav_ids]
            for person in our_persons:
                query = 'SELECT fav_id, display_name, twtv_id FROM dotaaccs WHERE friendid=$1'
                user = await self.bot.pool.fetchrow(query, person.account_id)
                log.debug(f'Our person: {user.display_name} - {await hero.name_by_id(person.hero_id)}')

                query = """ SELECT dotafeed_ch_id 
                            FROM guilds
                            WHERE $1=ANY(dotafeed_hero_ids) AND $2=ANY(dotafeed_stream_ids)
                        """
                rows = await self.bot.pool.fetch(query, person.hero_id, user.fav_id)

                channel_ids = [row.dotafeed_ch_id for row in rows]

                query = 'SELECT id FROM dfmatches WHERE match_id=$1'
                val = await self.bot.pool.fetchval(query, match.match_id)
                if val is None:
                    self.matches_to_send.append(
                        ActiveMatch(
                            match_id=match.match_id,
                            start_time=match.activate_time,
                            player_name=user.display_name,
                            twitchtv_id=user.twtv_id,
                            hero_id=person.hero_id,
                            hero_ids=[x.hero_id for x in match.players],
                            server_steam_id=match.server_steam_id,
                            channel_ids=channel_ids
                        )
                    )

    async def send_notifications(self, match: ActiveMatch):
        log.debug("Sending DotaFeed notification")
        for ch_id in match.channel_ids:
            ch = self.bot.get_channel(ch_id)
            if ch is None:
                continue

            em, img_file = await match.notif_embed_and_file(self.bot)
            em.title = f"{ch.guild.owner.name}'s fav hero + player spotted"
            msg = await ch.send(embed=em, file=img_file)
            query = """ INSERT INTO dfmatches (id, match_id, ch_id, hero_id, twitch_status) 
                        VALUES ($1, $2, $3, $4, $5)
                    """
            await self.bot.pool.execute(
                query, msg.id, match.match_id, ch.id, match.hero_id, match.twitch_status
            )

    async def declare_matches_finished(self):
        query = """ UPDATE dfmatches 
                    SET live=FALSE
                    WHERE NOT match_id=ANY($1) 
                    AND live IS DISTINCT FROM FALSE
                """
        await self.bot.pool.execute(
            query, list(self.top_source_dict.keys())
        )
        log.debug(f'--- Dota Feed: Task is finished ---')

    @tasks.loop(seconds=59)
    async def dotafeed(self):
        log.debug(f'--- Dota Feed: Task is starting now ---')

        await self.preliminary_queries()
        self.top_source_dict = {}
        for specific_games_flag in [False, True]:
            args = await self.get_args_for_top_source(specific_games_flag)
            self.bot.dota.request_top_source_tv_games(**args)
            self.bot.dota.wait_event('top_games_response', timeout=8)
        log.debug(f'len top_source_dict = {len(self.top_source_dict)}')

        self.matches_to_send = []
        await self.analyze_top_source_response()
        for match in self.matches_to_send:
            await self.send_notifications(match)

        await self.declare_matches_finished()

    @dotafeed.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @dotafeed.error
    async def dotafeed_error(self, error):
        # TODO: write if isinstance(RunTimeError): be silent else do send_traceback or something,
        #  probably declare your own error type
        await send_traceback(error, self.bot, embed=Embed(colour=Clr.error, title='Error in dotafeed'))
        # self.dotafeed.restart()


class AfterGameEdit(commands.Cog):
    def __init__(self, bot):
        self.bot: AluBot = bot
        self.after_match = []
        self.aftergame.start()

    def cog_unload(self) -> None:
        self.aftergame.cancel()

    async def after_match_games(self):
        self.after_match = []

        query = 'SELECT * FROM dfmatches WHERE live=FALSE'
        rows = await self.bot.pool.fetch(query)

        for row in rows:
            url = f"{ODOTA_API_URL}/request/{row.match_id}"
            async with self.bot.session.post(url) as resp:
                # print(resp)
                print(resp.ok)
                print(resp.headers['X-Rate-Limit-Remaining-Month'], resp.headers['X-Rate-Limit-Remaining-Minute'])
                print(await resp.json())

            url = f"{ODOTA_API_URL}/matches/{row.match_id}"
            async with self.bot.session.get(url) as resp:

                self.bot.update_odota_ratelimit(resp.headers)
                dic = await resp.json()
                if dic == {"error": "Not Found"}:
                    continue

                for player in dic.get('players', []):  # one day OpenDota freaked out
                    if player['hero_id'] == row.hero_id:
                        if player['purchase_log'] is not None:
                            print('!!!!!!!!!!!!holy shiet!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
                            self.after_match.append(
                                PostMatchPlayerData(
                                    player_data=player,
                                    channel_id=row.ch_id,
                                    message_id=row.id,
                                    twitch_status=row.twitch_status
                                )
                            )

    @tasks.loop(minutes=10)
    async def aftergame(self):
        log.debug('--- after game task starts now ---')
        await self.after_match_games()
        for player in self.after_match:
            await player.edit_the_embed(self.bot)

    @aftergame.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @aftergame.error
    async def dotafeed_error(self, error):
        # TODO: write if isinstance(RunTimeError): be silent else do send_traceback or something,
        #  probably declare your own error type
        await send_traceback(error, self.bot, embed=Embed(colour=Clr.error, title='Error in aftergame'))
        # self.dotafeed.restart()


class AddDotaPlayerFlags(commands.FlagConverter, case_insensitive=True):
    name: str
    steam: str
    twitch: bool


class RemoveStreamFlags(commands.FlagConverter, case_insensitive=True):
    name: Optional[str]
    steam: Optional[str]


async def hero_autocomplete(
    _interaction: Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    fruits = ['Banana', 'Pineapple', 'Apple', 'Watermelon', 'Melon', 'Cherry']
    return [
        app_commands.Choice(name=fruit, value=fruit)
        for fruit in fruits if current.lower() in fruit.lower()
    ]

class DotaFeedTools(commands.Cog, FPCBase, name='Dota 2'):
    """
    Commands to set up fav hero + player notifs.

    These commands allow you to choose players from our database as your favorite \
    (or you can request adding them if missing) and choose your favorite Dota 2 heroes. \
    The bot will send messages in a chosen channel when your fav player picks your fav hero.

    **Tutorial**
    1. Set channel with
    `$dota channel set #channel`
    2. Add players to your favourites, i.e.
    `$dota player add gorgc, bzm`
    List of available players can be seen with `$dota database list`
    3. Add missing players to the database , i.e.
    `$dota database add name: cr1tdota steam: 76561197986172872 twitch: yes`
    Only trustees can use `database add`. Others should `$dota database request` their fav streams.
    4. Add heroes to your favourites, i.e.
    `$dota hero add Dark Willow, Mirana, Anti-Mage`
    5. Use `remove` counterpart commands to `add` to edit out player/hero lists
    *Pro-Tip.* As shown for multiple hero/stream add/remove commands - use commas to separate names
    6. Ready ! More info below
    """

    def __init__(self, bot: AluBot):
        super().__init__(
            feature_name='DotaFeed',
            game_name='Dota 2',
            colour=Clr.prpl,
            bot=bot,
            players_table='dota_players',
            accounts_table='dota_accounts',
            channel_id_column='dotafeed_ch_id',
            players_column='dotafeed_stream_ids',
            acc_info_columns=['friend_id']
        )
        self.bot: AluBot = bot
        self.help_emote = Ems.DankLove

    def cog_load(self) -> None:
        self.bot.ini_twitch()

    @is_guild_owner()
    @commands.hybrid_group()
    @app_commands.default_permissions(administrator=True)
    async def dota(self, ctx: Context):
        """Group command about Dota, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @is_guild_owner()
    @dota.group(name='channel')
    async def dota_channel(self, ctx: Context):
        """Group command about Dota, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @is_guild_owner()
    @dota_channel.command(name='set', usage='[channel=curr]')
    @app_commands.describe(channel='Choose channel for DotaFeed notifications')
    async def dota_channel_set(self, ctx: Context, channel: Optional[TextChannel] = None):
        """Set channel to be the DotaFeed notifications channel."""
        await self.channel_set(ctx, channel)

    @is_guild_owner()
    @dota_channel.command(name='disable', description='Disable DotaFeed functionality.')
    async def dota_channel_disable(self, ctx: Context):
        """Stop getting DotaFeed notifs. Data about fav heroes/players won't be affected."""
        await self.channel_disable(ctx)

    @is_guild_owner()
    @dota_channel.command(name='check')
    async def dota_channel_check(self, ctx: Context):
        """Check if DotaFeed channel is set in the server."""
        await self.channel_check(ctx)

    @is_guild_owner()
    @dota.group(name='database', aliases=['db'])
    async def dota_database(self, ctx: Context):
        """Group command about Dota 2, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @staticmethod
    def player_acc_string(**kwargs):
        steam_id = kwargs.pop('id')
        friend_id = kwargs.pop('friend_id')
        return (
            f"`{steam_id}` - `{friend_id}`| " 
            f"[Steam](https://steamcommunity.com/profiles/{steam_id})" 
            f"/[Dotabuff](https://www.dotabuff.com/players/{friend_id})"
        )

    @is_guild_owner()
    @dota_database.command(name='list')
    async def dota_database_list(self, ctx: Context):
        """List of players in the database available for DotaFeed feature."""
        await self.database_list(ctx)

    @staticmethod
    def get_steam_id_and_64(steam_string: str):
        steam_acc = SteamID(steam_string)
        if steam_acc.type != EType.Individual:
            steam_acc = SteamID.from_url(steam_string)  # type: ignore # ValvePython does not care much about TypeHints

        if steam_acc is None or (hasattr(steam_acc, 'type') and steam_acc.type != EType.Individual):
            raise commands.BadArgument(
                    "Error checking steam profile for {steam}.\n"
                    "Check if your `steam` flag is correct steam id in either 64/32/3/2/friend_id representations "
                    "or just give steam profile link to the bot."
                )
        return steam_acc.as_64, steam_acc.id

    async def get_account_dict(
            self,
            *,
            steam_flag: str
    ) -> dict:
        steam_id, friend_id = self.get_steam_id_and_64(steam_flag)
        return {
            'id': steam_id,
            'friend_id': friend_id
        }

    @is_trustee()
    @dota_database.command(
        name='add',
        usage='name: <name> steam: <steam_id> twitch: <yes/no>',
        description='Add stream to the database.'
    )
    @app_commands.describe(
        name='Player name. If it is a twitch tv streamer then provide their twitch handle',
        steam='either steamid in any of 64/32/3/2 versions, friendid or just steam profile link',
        twitch='If you proved twitch handle for "name" then press `True` otherwise `False`',
    )
    async def dota_database_add(self, ctx: Context, *, flags: AddDotaPlayerFlags):
        """
        Add player to the database.
        • `<name>` is player name
        • `<steam_id>` is either steam_id in any of 64/32/3/2/friend_id versions or just Steam profile link.
        • `<twitch>` - yes/no indicating if player with name also streams under such name
        """
        await ctx.typing()
        player_dict = await self.get_player_dict(name_flag=flags.name, twitch_flag=flags.twitch)
        account_dict = await self.get_account_dict(steam_flag=flags.steam)
        await self.database_add(ctx, player_dict, account_dict)

    @is_guild_owner()
    @dota_database.command(
        name='request',
        usage='name: <name> steam: <steamid> twitch: <yes/no>',
        description='Request player to be added into the database.'
    )
    @app_commands.describe(
        name='player name',
        steam='either steam_id in any of 64/32/3/2 versions, friend_id or just steam profile link',
        twitch='is it a twitch.tv streamer? yes/no',
    )
    async def dota_database_request(self, ctx: Context, *, flags: AddDotaPlayerFlags):
        """
        Request player to be added into the database. \
        This will send a request message into Aluerie's personal logs channel.
        """
        await ctx.typing()

        player_dict = await self.get_player_dict(name_flag=flags.name, twitch_flag=flags.twitch)
        account_dict = await self.get_account_dict(steam_flag=flags.steam)
        await self.database_request(ctx, player_dict, account_dict, flags)

    @is_trustee()
    @dota_database.command(
        name='remove',
        usage='name: <name> steam: [steam_id]'
    )
    @app_commands.describe(
        name='twitch.tv stream name',
        steam='either steam_id in any of 64/32/3/2 versions, friend_id or just Steam profile link'
    )
    async def dota_database_remove(self, ctx: Context, *, flags: RemoveStreamFlags):
        """Remove player from the database."""
        await ctx.typing()
        if flags.steam:
            steam_id, friend_id = self.get_steam_id_and_64(flags.steam)
        else:
            steam_id = None
        await self.database_remove(ctx, flags.name.lower(), steam_id)

    @is_guild_owner()
    @dota.group(aliases=['streamer'])
    async def player(self, ctx: Context):
        """Group command about Dota 2, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @is_guild_owner()
    @player.command(with_app_command=False, name='add', usage='<player_name(-s)>')
    async def dota_player_add_ext(self, ctx: Context, *player_names):
        """Add player to your favourites."""

        await ctx.reply(' '.join(player_names))

    @is_guild_owner()
    @player.app_command.command(name='add')
    @app_commands.describe(player_names='Name(-s) of players')
    async def dota_player_add_slh(self, ctx: Context, *, player_names: str):
        """Add player to your favourites."""
        await ctx.reply(player_names)
        return
        #await self.player_add_remove(ctx, player_names, mode='add')


    async def player_add_remove(
            self,
            ctx: Context,
            player_names: str,
            mode: Literal['add', 'remov']
    ):
        """Work function for player add remove"""
        async def get_player(name: str):
            query = 'SELECT * FROM dotaaccs WHERE name=$1 LIMIT 1'
            player = await self.bot.pool.fetchrow(query, name.lower())
            return getattr(player, 'display_name', name), getattr(player, 'fav_id', None)

        data_dict = {
            'success': f'Successfully {mode}ed following players',
            'already': f'Stream(-s) already {"not" if mode == "remov" else ""} in fav list',
            'fail': 'Could not find players in the database with these names:',
            'fail_footer':
                'Check your argument or '
                'consider adding (for trustees)/requesting such streamer with '
                '`$dota database add/request name: <name> steam: <steamid> twitch: <yes/no>`'
        }
        query = 'SELECT dotafeed_stream_ids FROM guilds WHERE id=$1'
        val = await self.bot.pool.fetchval(query, ctx.guild.id)
        new_ids, embed_list = await self.sort_out_names(
            player_names, val, mode, data_dict, get_player
        )
        query = 'UPDATE guilds SET dotafeed_stream_ids=$1 WHERE id=$2'
        await self.bot.pool.execute(query, new_ids, ctx.guild.id)
        for em in embed_list:
            await ctx.reply(embed=em)

    async def player_add_remove_autocomplete(
            self,
            ntr: Interaction,
            current: str,
            mode: Literal['add', 'remov']
    ) -> List[app_commands.Choice[str]]:
        query = 'SELECT dotafeed_stream_ids FROM guilds WHERE id=$1'
        fav_ids = await self.bot.pool.fetchval(query, ntr.guild.id)

        query = 'SELECT display_name, fav_id FROM dotaaccs'
        rows = await self.bot.pool.fetch(query)
        fav_items = list(set([row.display_name for row in rows if row.fav_id in fav_ids]))
        all_items = list(set([row.display_name for row in rows]))

        return await self.add_remove_autocomplete_work(
            current,
            mode,
            all_items=all_items,
            fav_items=fav_items,
        )

    #@dota_player_add_slh.autocomplete('player_names')
    async def player_add_autocomplete(
            self,
            ntr: Interaction,
            current: str
    ) -> List[app_commands.Choice[str]]:
        return await self.player_add_remove_autocomplete(ntr, current, mode='add')

    @is_guild_owner()
    @player.command(name='remove', usage='<player_name(-s)>')
    @app_commands.describe(player_names='Name(-s) of players')
    async def player_remove(self, ctx: Context, *, player_names: str):
        """Remove player from your favourites."""
        await self.player_add_remove(ctx, player_names, mode='remov')

    @player_remove.autocomplete('player_names')
    async def player_remove_autocomplete(
            self,
            ntr: Interaction,
            current: str
    ) -> List[app_commands.Choice[str]]:
        return await self.player_add_remove_autocomplete(ntr, current, mode='remov')

    @is_guild_owner()
    @player.command(name='list')
    async def player_list(self, ctx: Context):
        """Show current list of fav players."""
        query = 'SELECT dotafeed_stream_ids FROM guilds WHERE id=$1'
        favid_list = await self.bot.pool.fetchval(query, ctx.guild.id)

        query = f""" SELECT display_name, twtv_id 
                    FROM dotaaccs
                    WHERE fav_id = ANY ($1)
                    ORDER BY display_name
                """
        rows = await self.bot.pool.fetch(query, favid_list)
        names_list = {row.display_name: row.twtv_id for row in rows}

        ans_array = [
            self.player_name_string(name, tw)
            for name, tw in names_list.items()
        ]
        ans_array = sorted(list(set(ans_array)), key=str.casefold)
        em = Embed(
            color=Clr.prpl,
            title='List of fav dota 2 players',
            description="\n".join(ans_array)
        )
        await ctx.reply(embed=em)

    @is_guild_owner()
    @dota.group()
    async def hero(self, ctx: Context):
        """Group command about Dota 2, for actual commands use it together with subcommands"""
        await ctx.scnf()

    async def hero_add_remove(self, ctx: Context, hero_names, mode):
        async def get_proper_name_and_id(hero_name: str):
            try:
                hero_id = await hero.id_by_name(hero_name)
                proper_hero_name = await hero.name_by_id(hero_id)
                return proper_hero_name, hero_id
            except KeyError:
                return hero_name, None

        data_dict = {
            'success': f'Successfully {mode}ed following heroes',
            'already': f'Hero(-s) already {"not" if mode == "remov" else ""} in fav list',
            'fail': 'Could not recognize Dota 2 heroes from these names',
            'fail_footer': 'You can look in $help for help in hero names'
        }
        query = 'SELECT dotafeed_hero_ids FROM guilds WHERE id=$1'
        val = await self.bot.pool.fetchval(query, ctx.guild.id)
        new_ids, embed_list = await self.sort_out_names(
            hero_names, val, mode, data_dict, get_proper_name_and_id
        )
        query = 'UPDATE guilds SET dotafeed_hero_ids=$1 WHERE id=$2'
        await self.bot.pool.execute(query, new_ids, ctx.guild.id)
        for em in embed_list:
            await ctx.reply(embed=em)

    async def hero_add_remove_autocomplete_work(
            self,
            ntr: Interaction,
            current: str,
            mode: Literal['add', 'remov']
    ) -> List[app_commands.Choice[str]]:
        query = 'SELECT dotafeed_hero_ids FROM guilds WHERE id=$1'
        fav_hero_ids = await self.bot.pool.fetchval(query, ntr.guild.id)

        data = await hero.hero_keys_cache.data
        all_hero_dict = data['name_by_id']
        all_hero_dict.pop(0, None)

        return await self.add_remove_autocomplete_work(
            current,
            mode,
            all_items=list(all_hero_dict.keys()),
            fav_items=fav_hero_ids,
            func=hero.name_by_id,
            reverse_func=hero.id_by_name
        )






    @hero.command(with_app_command=False, name='add')
    async def hero_add_ctx(self, ctx: Context, *, hero_names: str):
        await ctx.reply(hero_names)

    @hero.app_command.command(name='add')
    @app_commands.autocomplete(
        hero_name1=hero_autocomplete,
        hero_name2=hero_autocomplete,
        hero_name3=hero_autocomplete
    )
    async def hero_add_ntr(self, ntr: Interaction, hero_name1: str, hero_name2: str, hero_name3: str):
        hero_names = [hero_name1, hero_name2, hero_name3]
        await ntr.response.send_message(', '.join(hero_names))








    """@is_guild_owner()
    @hero.command(
        name='add',
        usage='<hero_name(-s)>',
        description='Add hero(-es) to your fav heroes list.'
    )
    @app_commands.describe(hero_names='Name(-s) from Dota 2 Hero Grid')
    async def hero_add(self, ctx: Context, *, hero_names: str):
        
        Add hero(-es) to your fav heroes list. \
        Use names from Dota 2 hero grid. For example,
        • `Anti-Mage` (letter case does not matter) and not `Magina`;
        • `Queen of Pain` and not `QoP`.
        
        # At last, you can find proper name
        # [here](https://api.opendota.com/api/constants/heroes) with Ctrl+F \
        # under one of `"localized_name"`
        await self.hero_add_remove(ctx, hero_names, mode='add')"""

    #@hero_add.autocomplete('hero_names')
    async def hero_add_autocomplete(
            self,
            ntr: Interaction,
            current: str
    ) -> List[app_commands.Choice[str]]:
        return await self.hero_add_remove_autocomplete_work(ntr, current, mode='add')

    @is_guild_owner()
    @hero.command(
        name='remove',
        usage='<hero_name(-s)>'
    )
    @app_commands.describe(hero_names='Name(-s) from Dota 2 Hero Grid')
    async def hero_remove(self, ctx: Context, *, hero_names: str):
        """Remove hero(-es) from your fav heroes list."""
        await self.hero_add_remove(ctx, hero_names, mode='remov')

    @hero_remove.autocomplete('hero_names')
    async def hero_add_autocomplete(
            self,
            ntr: Interaction,
            current: str
    ) -> List[app_commands.Choice[str]]:
        return await self.hero_add_remove_autocomplete_work(ntr, current, mode='remov')

    @is_guild_owner()
    @hero.command(name='list')
    async def hero_list(self, ctx: Context):
        """Show current list of fav heroes."""
        await ctx.typing()
        query = 'SELECT dotafeed_hero_ids FROM guilds WHERE id=$1'
        hero_list = await ctx.pool.fetchval(query, ctx.guild.id)
        answer = [f'`{await hero.name_by_id(h_id)} - {h_id}`' for h_id in hero_list]
        answer.sort()
        em = Embed(
            color=Clr.prpl,
            title='List of fav dota 2 heroes',
            description='\n'.join(answer)
        )
        await ctx.reply(embed=em)

    @is_guild_owner()
    @dota.command(description='Turn on/off spoiling resulting stats for matches. ')
    @app_commands.describe(spoil='`Yes` to enable spoiling with stats, `No` for disable')
    async def spoil(
            self,
            ctx: Context,
            spoil: bool
    ):
        """
        Turn on/off spoiling resulting stats for matches.
        It is "on" by default, so it can show what items players finished with and KDA.
        """
        query = 'UPDATE guilds SET dotafeed_spoils_on=$1 WHERE id=$2'
        await self.bot.pool.execute(query, spoil, ctx.guild.id)
        em = Embed(
            colour=Clr.prpl,
            description=f"Changed spoil value to {spoil}"
        )
        await ctx.reply(embed=em)


class DotaAccCheck(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
        self.check_acc_renames.start()

    def cog_unload(self) -> None:
        self.check_acc_renames.cancel()

    @tasks.loop(time=time(hour=12, minute=11, tzinfo=timezone.utc))
    async def check_acc_renames(self):
        query = 'SELECT id, twtv_id, display_name FROM dotaaccs WHERE twtv_id IS NOT NULL'
        rows = await self.bot.pool.fetch(query)

        for row in rows:
            display_name: str = self.bot.twitch.name_by_twitch_id(row.twtv_id)
            if display_name != row.display_name:
                query = 'UPDATE dotaaccs SET display_name=$1, name=$2 WHERE id=$3'
                await self.bot.pool.execute(query, display_name, display_name.lower(), row.id)

    @check_acc_renames.before_loop
    async def before(self):
        log.info("check_acc_renames before the loop")
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(DotaFeed(bot))
    await bot.add_cog(AfterGameEdit(bot))
    await bot.add_cog(DotaFeedTools(bot))
    if datetime.now(timezone.utc).day == 16:
        await bot.add_cog(DotaAccCheck(bot))
