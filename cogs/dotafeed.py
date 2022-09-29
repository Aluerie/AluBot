from __future__ import annotations

from datetime import datetime, timezone, time
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import func
from steam.core.msg import MsgProto
from steam.enums import emsg
from steam.steamid import SteamID, EType
import vdf

from discord import Embed, TextChannel, app_commands
from discord.ext import commands, tasks

from utils import database as db
from utils.checks import is_guild_owner, is_trustee
from utils.dota import hero
from utils.dota.const import ODOTA_API_URL
from utils.dota.models import PlayerAfterMatch, ActiveMatch
from utils.feedtools import FeedTools
from utils.twitch import name_by_twitchid
from utils.var import *
from utils.distools import send_traceback, send_pages_list

if TYPE_CHECKING:
    from discord import Interaction
    from utils.bot import AluBot
    from utils.context import Context

import logging

log = logging.getLogger('root')
log.setLevel(logging.WARNING)  # INFO) WARNING)


class DotaFeed(commands.Cog):
    def __init__(self, bot):
        self.bot: AluBot = bot
        self.dotafeed.start()
        self.lobby_ids = set()
        self.active_matches = []
        self.after_match = []

    def cog_unload(self) -> None:
        self.dotafeed.cancel()

    async def after_match_games(self, ses):
        log.info("after match after match")
        self.after_match = []

        for row in ses.query(db.em):
            url = f"{ODOTA_API_URL}/request/{row.match_id}"
            async with self.bot.ses.post(url):
                pass
            url = f"{ODOTA_API_URL}/matches/{row.match_id}"
            async with self.bot.ses.get(url) as resp:
                dic = await resp.json()
                if dic == {"error": "Not Found"}:
                    continue

                for player in dic.get('players', []):  # one day OD freaked out
                    if player['hero_id'] == row.hero_id:
                        if player['purchase_log'] is not None:
                            self.after_match.append(
                                PlayerAfterMatch(
                                    data=player,
                                    channel_id=row.ch_id,
                                    message_id=row.id,
                                    twitch_status=row.twitch_status
                                )
                            )

    async def try_to_find_games(self, db_ses):
        log.info("TryToFindGames dota2info")

        self.active_matches = []
        self.lobby_ids = set()

        def get_all_fav_ids(column_name: str):
            ids = []
            for r in db_ses.query(db.ga):
                ids += getattr(r, column_name, [])
            return list(set(ids))

        fav_hero_ids = get_all_fav_ids('dotafeed_hero_ids')
        fav_player_ids = get_all_fav_ids('dotafeed_stream_ids')

        self.bot.steam_dota_login()

        # @dota.on('ready')
        def ready_function():
            log.info("ready_function dota2info")
            self.bot.dota.request_top_source_tv_games(lobby_ids=list(self.lobby_ids))

        # @dota.on('top_source_tv_games')
        def response(result):
            log.info(f"top_source_tv_games resp ng: {result.num_games} sg: {result.specific_games}")
            if result.specific_games:
                friendids = [r.friendid for r in db_ses.query(db.d.friendid)]
                for match in result.game_list:  # games
                    our_persons = [x for x in match.players if x.account_id in friendids and x.hero_id in fav_hero_ids]
                    for person in our_persons:
                        user = db_ses.query(db.d).filter_by(friendid=person.account_id).first()

                        # print(user.display_name, person.hero_id)
                        for row in db_ses.query(db.ga):
                            if db_ses.query(db.em).filter_by(
                                    match_id=match.match_id,
                                    ch_id=row.dotafeed_ch_id,
                                    hero_id=person.hero_id
                            ).first() is None and \
                                    person.hero_id in row.dotafeed_hero_ids and \
                                    user.fav_id in row.dotafeed_stream_ids:
                                self.active_matches.append(
                                    ActiveMatch(
                                        match_id=match.match_id,
                                        start_time=match.activate_time,
                                        player_name=user.display_name,
                                        twitchtv_id=user.twtv_id,
                                        hero_id=person.hero_id,
                                        hero_ids=[x.hero_id for x in match.players],
                                        server_steam_id=match.server_steam_id,
                                        channel_id=row.dotafeed_ch_id
                                    )
                                )
                log.info(f'to_be_posted {self.active_matches}')
            self.bot.dota.emit('top_games_response')

        proto_msg = MsgProto(emsg.EMsg.ClientRichPresenceRequest)
        proto_msg.header.routing_appid = 570

        steamids = [row.id for row in db_ses.query(db.d).filter(db.d.fav_id.in_(fav_player_ids)).all()]
        proto_msg.body.steamid_request.extend(steamids)
        resp = self.bot.steam.send_message_and_wait(proto_msg, emsg.EMsg.ClientRichPresenceInfo, timeout=8)
        if resp is None:
            print('resp is None, hopefully everything else will be fine tho;')
            return
        for item in resp.rich_presence:
            if rp_bytes := item.rich_presence_kv:
                # steamid = item.steamid_user
                rp = vdf.binary_loads(rp_bytes)['RP']
                # print(rp)
                if lobby_id := int(rp.get('WatchableGameID', 0)):
                    if rp.get('param0', 0) == '#DOTA_lobby_type_name_ranked':
                        if await hero.id_by_npcname(rp.get('param2', '#')[1:]) in fav_hero_ids:  # that's npcname
                            self.lobby_ids.add(lobby_id)

        # print(lobbyids)
        log.info(f'lobbyids {self.lobby_ids}')
        # dota.on('ready', ready_function)
        self.bot.dota.once('top_source_tv_games', response)
        ready_function()
        self.bot.dota.wait_event('top_games_response', timeout=8)

    @tasks.loop(seconds=59)
    async def dotafeed(self):
        log.info('========================================')
        with db.session_scope() as db_ses:
            await self.try_to_find_games(db_ses)
            for match in self.active_matches:
                await match.send_the_embed(self.bot, db_ses)

            await self.after_match_games(db_ses)
            for player in self.after_match:
                await player.edit_the_embed(self.bot, db_ses)

    @dotafeed.before_loop
    async def before(self):
        log.info("dotafeed before loop wait")
        await self.bot.wait_until_ready()

    @dotafeed.error
    async def dotafeed_error(self, error):
        # TODO: write if isinstance(RunTimeError): be silent else do send_traceback or something,
        #  probably declare your own error type
        await send_traceback(error, self.bot, embed=Embed(colour=Clr.error, title='Error in dotafeed'))
        # self.dotafeed.restart()


class AddStreamFlags(commands.FlagConverter, case_insensitive=True):
    name: str
    steam: str
    twitch: bool


class RemoveStreamFlags(commands.FlagConverter, case_insensitive=True):
    name: str
    steam: Optional[str]


class DotaFeedTools(commands.Cog, FeedTools, name='Dota 2'):
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

    def __init__(self, bot):
        super().__init__(
            display_name='DotaFeed',
            db_name='dotafeed',
            game_name='Dota 2',
            db_acc_class=db.d,
            clr=Clr.prpl
        )
        self.bot = bot
        self.help_emote = Ems.DankLove

    @is_guild_owner()
    @commands.hybrid_group()
    @app_commands.default_permissions(administrator=True)
    async def dota(self, ctx: Context):
        """Group command about Dota, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @is_guild_owner()
    @dota.group(name='channel')
    async def channel_(self, ctx: Context):
        """Group command about Dota, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @is_guild_owner()
    @channel_.command(name='set', usage='[channel=curr]')
    @app_commands.describe(channel='Choose channel for DotaFeed notifications')
    async def channel_set(self, ctx: Context, channel: Optional[TextChannel] = None):
        """Set channel to be the DotaFeed notifications channel."""
        await self.channel_set_base(ctx, channel)

    @is_guild_owner()
    @channel_.command(name='disable', description='Disable DotaFeed functionality.')
    async def channel_disable(self, ctx: Context):
        """Stop getting DotaFeed notifs. Data about fav heroes/players won't be affected."""
        await self.channel_disable_base(ctx)

    @is_guild_owner()
    @channel_.command(name='check')
    async def channel_check(self, ctx: Context):
        """Check if DotaFeed channel is set in the server."""
        await self.channel_check_base(ctx)

    @is_guild_owner()
    @dota.group(aliases=['db'])
    async def database(self, ctx: Context):
        """Group command about Dota 2, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @staticmethod
    def field_player_data(steamid, friendid):
        return \
            f"`{steamid}` - `{friendid}`| " \
            f"[Steam](https://steamcommunity.com/profiles/{steamid})" \
            f"/[Dotabuff](https://www.dotabuff.com/players/{friendid})"

    def field_both(self, display_name, twitch, steamid, friendid):
        return \
            f'{self.field_player_name(display_name, twitch)}\n' \
            f'{self.field_player_data(steamid, friendid)}'

    @is_guild_owner()
    @database.command(name='list')
    async def database_list(self, ctx: Context):
        """List of players in the database available for DotaFeed feature."""
        await ctx.typing()
        twtvid_list = db.get_value(db.ga, ctx.guild.id, 'dotafeed_stream_ids')
        ss_dict = dict()
        for row in db.session.query(db.d):
            followed = f' {Ems.DankLove}' if row.fav_id in twtvid_list else ''
            key = f"{self.field_player_name(row.display_name, row.twtv_id)}{followed}"
            if key not in ss_dict:
                ss_dict[key] = []
            ss_dict[key].append(self.field_player_data(row.id, row.friendid))

        ans_array = [f"{k}\n {chr(10).join(ss_dict[k])}" for k in ss_dict]
        ans_array = sorted(list(set(ans_array)), key=str.casefold)

        await send_pages_list(
            ctx,
            ans_array,
            split_size=10,
            colour=Clr.prpl,
            title="List of Dota 2 Streams in Database",
            footer_text=f'With love, {ctx.guild.me.display_name}'
        )

    @staticmethod
    async def get_steam_id_and_64(ctx: Context, steam: str):
        steam_acc = SteamID(steam)
        if steam_acc.type != EType.Individual:
            steam_acc = SteamID.from_url(steam)  # type: ignore # ValvePython does not care much about TypeHints

        if steam_acc is None or (hasattr(steam_acc, 'type') and steam_acc.type != EType.Individual):
            em = Embed(
                colour=Clr.error,
                description=
                f'Error checking steam profile for {steam}.\n '
                f'Check if your `steam` flag is correct steam id in either 64/32/3/2/friendid representations '
                f'or just give steam profile link to the bot.'
            )
            await ctx.reply(embed=em, ephemeral=True)
            return None, None

        return steam_acc.as_64, steam_acc.id

    async def database_add_request_check(self, ctx: Context, flags: AddStreamFlags):
        if flags.twitch:
            twtv_id = await self.get_check_twitch_id(ctx, flags.name.lower())
            if twtv_id is None:
                return False
        else:
            twtv_id = None

        steamid, friendid = await self.get_steam_id_and_64(ctx, flags.steam)
        if steamid is None:
            return False

        if (user := db.session.query(db.d).filter_by(id=steamid).first()) is not None:
            em = Embed(
                colour=Clr.error
            ).add_field(
                name=f'This steam account is already in the database',
                value=
                f'It is marked as {user.name}\'s account.\n\n'
                f'Did you mean to use `$dota stream add {user.name}` to add the stream into your fav list?'
            )
            await ctx.reply(embed=em, ephemeral=True)
            return False

        old_max_fav_id = int(db.session.query(func.max(db.d.fav_id)).scalar() or 0)
        db.append_row(
            db.d,
            name=flags.name.lower(),
            display_name=flags.name,
            id=steamid,
            friendid=friendid,
            twtv_id=twtv_id,
            fav_id=old_max_fav_id + 1
        )
        return self.field_both(flags.name, twtv_id, steamid, friendid)

    @is_trustee()
    @database.command(
        name='add',
        usage='name: <name> steam: <steamid> twitch: <yes/no>',
        description='Add stream to the database.'
    )
    @app_commands.describe(
        name='player name',
        steam='either steamid in any of 64/32/3/2 versions, friendid or just steam profile link',
        twitch='is it a twitch.tv streamer? yes/no',
    )
    async def database_add(self, ctx: Context, *, flags: AddStreamFlags):
        """
        Add player to the database.
        • `<name>` is player name
        • `<steamid>` is either steamid in any of 64/32/3/2/friendid versions or just steam profile link.
        • `<twitch>` - yes/no indicating if player with name also streams under such name
        """
        await ctx.typing()

        answer = await self.database_add_request_check(ctx, flags)
        if answer is False:
            return

        em = Embed(
            colour=Clr.prpl
        ).add_field(
            name=f'Successfully added the account to the database',
            value=answer
        )
        await ctx.reply(embed=em)
        em.colour = MP.green(shade=200)
        em.set_author(name=ctx.author, icon_url=ctx.author.avatar.url)
        await self.bot.get_channel(Cid.global_logs).send(embed=em)

    @is_trustee()
    @database.command(
        name='remove',
        usage='name: <name> steam: [steamid]'
    )
    @app_commands.describe(
        name='twitch.tv stream name',
        steam='either steamid in any of 64/32/3/2 versions, friendid or just steam profile link'
    )
    async def database_remove(self, ctx: Context, *, flags: RemoveStreamFlags):
        """Remove player from the database."""
        await ctx.typing()

        map_dict = {'name': flags.name.lower()}
        if flags.steam:
            steamid, friendid = await self.get_steam_id_and_64(ctx, flags.steam)
            if steamid is None:
                return
            map_dict['id'] = steamid

        success = []
        with db.session_scope() as ses:
            query = ses.query(db.d).filter_by(**map_dict)
            for row in query:
                success.append(
                    {
                        'name': row.name,
                        'id': row.id,
                        'friendid': row.friendid,
                        'twtv_id': row.twtv_id
                    }
                )
            query.delete()
        if success:
            em = Embed(
                colour=Clr.prpl,
            ).add_field(
                name='Successfully removed account(-s) from the database',
                value=
                '\n'.join(self.field_both(x['name'], x['twtv_id'], x['id'], x['friendid']) for x in success)
            )
            await ctx.reply(embed=em)

            em.colour = MP.red(shade=200)
            em.set_author(name=ctx.author, icon_url=ctx.author.avatar.url)
            await self.bot.get_channel(Cid.global_logs).send(embed=em)
        else:
            em = Embed(
                colour=Clr.error
            ).add_field(
                name='There is no account in the database like that',
                value=' '.join([f'{k}: {v}' for k, v in flags.__dict__.items()])
            )
            await ctx.reply(embed=em)

    @is_guild_owner()
    @database.command(
        name='request',
        usage='name: <name> steam: <steamid> twitch: <yes/no>',
        description='Request player to be added into the database.'
    )
    @app_commands.describe(
        name='player name',
        steam='either steamid in any of 64/32/3/2 versions, friendid or just steam profile link',
        twitch='is it a twitch.tv streamer? yes/no',
    )
    async def database_request(self, ctx: Context, *, flags: AddStreamFlags):
        """
        Request player to be added into the database. \
        This will send a request message into Aluerie's personal logs channel.
        """
        await ctx.typing()

        answer = await self.database_add_request_check(ctx, flags)
        if answer is False:
            return

        warn_em = Embed(
            colour=Clr.prpl,
            title='Confirmation Prompt',
            description=
            f'Are you sure you want to request this streamer steam account to be added into the database?\n'
            f'This information will be sent to Aluerie. Please, double check before confirming.'
        ).add_field(
            name='Request to add an account into the database',
            value=answer
        )
        confirm = await ctx.prompt(embed=warn_em)
        if not confirm:
            return await ctx.send('Aborting...', delete_after=5.0)

        warn_em.colour = MP.orange(shade=200)
        warn_em.description = ''
        warn_em.set_author(name=ctx.author, icon_url=ctx.author.avatar.url)
        cmd_str = ' '.join(f'{k}: {v}' for k, v in flags.__dict__.items())
        warn_em.add_field(
            name='Command',
            value=f'`$dota stream add {cmd_str}'
        )
        await self.bot.get_channel(Cid.global_logs).send(embed=warn_em)

    @is_guild_owner()
    @dota.group(aliases=['streamer'])
    async def player(self, ctx: Context):
        """Group command about Dota 2, for actual commands use it together with subcommands"""
        await ctx.scnf()

    async def player_add_remove(
            self,
            ctx: Context,
            player_names: str,
            mode: Literal['add', 'remov']
    ):
        """Work function for player add remove"""
        async def get_player(name: str):
            player = db.session.query(db.d).filter_by(name=name.lower()).first()
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
        new_ids, embed_list = await self.sort_out_names(
            player_names,
            db.get_value(db.ga, ctx.guild.id, 'dotafeed_stream_ids'),
            mode,
            data_dict,
            get_player
        )
        db.set_value(db.ga, ctx.guild.id, dotafeed_stream_ids=new_ids)
        for em in embed_list:
            await ctx.reply(embed=em)

    @staticmethod
    async def player_add_remove_autocomplete(
            ntr: Interaction,
            current: str,
            mode: Literal['add', 'remov']
    ) -> List[app_commands.Choice[str]]:
        my_fav_ids = db.get_value(db.ga, ntr.guild.id, 'dotafeed_stream_ids')
        if mode == 'add':
            all_player_names = [row.display_name for row in db.session.query(db.d) if row.fav_id not in my_fav_ids]
        elif mode == 'remov':
            all_player_names = [row.display_name for row in db.session.query(db.d) if row.fav_id in my_fav_ids]
        else:
            return []
        all_player_names = list(set(all_player_names))
        all_player_names.sort()
        return [
            app_commands.Choice(name=clr, value=clr)
            for clr in all_player_names if current.lower() in clr.lower()
        ][:25]

    @is_guild_owner()
    @player.command(name='add', usage='<player_name(-s)>')
    @app_commands.describe(player_names='Name(-s) of players')
    async def player_add(self, ctx: Context, *, player_names: str):
        """Add player to your favourites."""
        await self.player_add_remove(ctx, player_names, mode='add')

    @player_add.autocomplete('player_names')
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
        favid_list = db.get_value(db.ga, ctx.guild.id, 'dotafeed_stream_ids')
        names_list = {
            row.display_name: row.twtv_id
            for row in db.session.query(db.d).filter(db.d.fav_id.in_(favid_list)).all()  # type: ignore
        }

        ans_array = [
            self.field_player_name(name, tw)
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

    async def hero_add_remove(self, ctx, hero_names, mode):
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
        new_ids, embed_list = await self.sort_out_names(
            hero_names,
            db.get_value(db.ga, ctx.guild.id, 'dotafeed_hero_ids'),
            mode,
            data_dict,
            get_proper_name_and_id
        )
        db.set_value(db.ga, ctx.guild.id, dotafeed_hero_ids=new_ids)
        for em in embed_list:
            await ctx.reply(embed=em)

    @staticmethod
    async def hero_add_remove_autocomplete_work(
            ntr: Interaction,
            current: str,
            mode: Literal['add', 'remov']
    ) -> List[app_commands.Choice[str]]:
        fav_hero_ids = db.get_value(db.ga, ntr.guild.id, 'dotafeed_hero_ids')

        data = await hero.hero_keys_cache.data
        all_hero_dict = data['name_by_id']
        all_hero_dict.pop(0, None)
        if mode == 'add':
            answer = [hid for hid, name in all_hero_dict.items() if hid not in fav_hero_ids]
        elif mode == 'remov':
            answer = [hid for hid, name in all_hero_dict.items() if hid in fav_hero_ids]
        else:
            return []
        answer = [await hero.name_by_id(h_id) for h_id in answer]
        answer.sort()
        return [
            app_commands.Choice(name=clr, value=clr)
            for clr in answer if current.lower() in clr.lower()
        ][:25]

    @is_guild_owner()
    @hero.command(
        name='add',
        usage='<hero_name(-s)>',
        description='Add hero(-es) to your fav heroes list.'
    )
    @app_commands.describe(hero_names='Name(-s) from Dota 2 Hero Grid')
    async def hero_add(self, ctx: Context, *, hero_names: str):
        """
        Add hero(-es) to your fav heroes list. \
        Use names from Dota 2 hero grid. For example,
        • `Anti-Mage` (letter case does not matter) and not `Magina`;
        • `Queen of Pain` and not `QoP`.
        """
        # At last, you can find proper name
        # [here](https://api.opendota.com/api/constants/heroes) with Ctrl+F \
        # under one of `"localized_name"`
        await self.hero_add_remove(ctx, hero_names, mode='add')

    @hero_add.autocomplete('hero_names')
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
        hero_list = db.get_value(db.ga, ctx.guild.id, 'dotafeed_hero_ids')
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
        db.set_value(db.ga, ctx.guild.id, dotafeed_spoils_on=spoil)
        em = Embed(
            colour=Clr.prpl,
            description=f"Changed spoil value to {spoil}"
        )
        await ctx.reply(embed=em)


class DotaAccCheck(commands.Cog):
    def __init__(self, bot):
        self.bot: AluBot = bot
        self.check_acc_renames.start()

    def cog_unload(self) -> None:
        self.check_acc_renames.cancel()

    @tasks.loop(time=time(hour=12, minute=11, tzinfo=timezone.utc))
    async def check_acc_renames(self):
        with db.session_scope() as ses:
            for row in ses.query(db.d):
                if row.twtv_id is not None:
                    name = name_by_twitchid(row.twtv_id)
                    if name != row.display_name:
                        row.display_name = name
                        row.name = name.lower()

    @check_acc_renames.before_loop
    async def before(self):
        log.info("check_acc_renames before the loop")
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(DotaFeed(bot))
    await bot.add_cog(DotaFeedTools(bot))
    if datetime.now(timezone.utc).day == 16:
        await bot.add_cog(DotaAccCheck(bot))
