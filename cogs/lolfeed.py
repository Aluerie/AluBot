from __future__ import annotations

import logging
from datetime import datetime, timezone, time
from typing import TYPE_CHECKING, Optional, List

from discord import Embed, app_commands, TextChannel, Permissions
from discord.ext import commands, tasks

from pyot.core.exceptions import NotFound, ServerError
from pyot.utils.lol import champion
from roleidentification import pull_data


from .lol.const import *
from .lol.const import LiteralServerUpper
from .lol.models import LiveMatch, PostMatchPlayer, Account
from .lol.utils import get_diff_list, get_all_champ_names
from .utils.checks import is_owner, is_guild_owner, is_trustee
from .utils.context import Context
from .utils.fpc import FPCBase
from .utils.var import Clr, Ems

# need to import the last because in import above we activate 'lol' model
from pyot.models import lol

if TYPE_CHECKING:
    from .utils.bot import AluBot
    from discord import Interaction

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class LoLFeedNotifications(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
        self.live_matches: List[LiveMatch] = []
        self.all_live_match_ids: List[int] = []
        self.lolfeed_notifs.start()

    async def cog_load(self) -> None:
        await self.bot.ini_twitch()

    def cog_unload(self) -> None:
        self.lolfeed_notifs.cancel()

    async def fill_live_matches(self):
        self.live_matches, self.all_live_match_ids = [], []

        query = 'SELECT DISTINCT(unnest(lolfeed_champ_ids)) FROM guilds'
        fav_champ_ids = [r for r, in await self.bot.pool.fetch(query)]  # row.unnest

        live_fav_player_ids = await self.bot.twitch.get_live_lol_player_ids(pool=self.bot.pool)

        query = 'SELECT * FROM lol_accounts WHERE player_id=ANY($1)'
        for r in await self.bot.pool.fetch(query, live_fav_player_ids):
            try:
                live_game = await lol.spectator.CurrentGame(summoner_id=r.id, platform=r.platform).get()
            except NotFound:
                continue
            except ServerError:
                log.debug(f'ServerError `lolfeed.py`: {r.account} {r.platform} {r.player_id}')
                continue
                # embed = Embed(colour=Clr.error)
                # embed.description = f'ServerError `lolfeed.py`: {row.name} {row.platform} {row.accname}'
                # await self.bot.get_channel(Cid.spam_me).send(embed=embed)  # content=umntn(Uid.alu)

            if not hasattr(live_game, 'queue_id') or live_game.queue_id != SOLO_RANKED_5v5_QUEUE_ENUM:
                continue
            self.all_live_match_ids.append(live_game.id)
            p = next((x for x in live_game.participants if x.summoner_id == r.id), None)
            if p.champion_id in fav_champ_ids \
                    and r.last_edited != f'{live_game.platform.upper()}_{live_game.id}':
                query = """ SELECT lolfeed_ch_id 
                            FROM guilds
                            WHERE $1=ANY(lolfeed_champ_ids) 
                                AND $2=ANY(lolfeed_stream_ids)
                                AND NOT lolfeed_ch_id=ANY(
                                    SELECT channel_id
                                    FROM lol_messages
                                    WHERE match_id=$3
                                )     
                        """
                channel_ids = [
                    i for i, in await self.bot.pool.fetch(query, p.champion_id, r.player_id, live_game.id)
                ]
                if channel_ids:
                    query = """ SELECT id, display_name, twitch_id 
                                FROM lol_players 
                                WHERE id=(
                                    SELECT player_id 
                                    FROM lol_accounts 
                                    WHERE lol_accounts.id=$1
                                )
                            """
                    user = await self.bot.pool.fetchrow(query, p.summoner_id)
                    log.debug(f'LF | {user.display_name} - {await champion.key_by_id(p.champion_id)}')
                    self.live_matches.append(
                        LiveMatch(
                            match_id=live_game.id,
                            platform=p.platform,
                            account_name=p.summoner_name,
                            start_time=round(live_game.start_time_millis / 1000),
                            champ_id=p.champion_id,
                            all_champ_ids=[player.champion_id for player in live_game.participants],
                            twitch_id=user.twitch_id,
                            spells=p.spells,
                            runes=p.runes,
                            channel_ids=channel_ids
                        )
                    )

    async def send_notifications(self, match: LiveMatch):
        log.debug("LF | Sending DotaFeed notification")
        for ch_id in match.channel_ids:
            if (ch := self.bot.get_channel(ch_id)) is None:
                log.debug("LF | The channel is None")
                continue

            em, img_file = await match.notif_embed_and_file(self.bot)
            log.debug('LF | Successfully made embed+file')
            em.title = f"{ch.guild.owner.name}'s fav champ + player spotted"
            msg = await ch.send(embed=em, file=img_file)

            query = """ INSERT INTO lol_matches (id, region, platform)
                        VALUES ($1, $2, $3)
                        ON CONFLICT DO NOTHING 
                    """
            await self.bot.pool.execute(query, match.match_id, platform_to_region(match.platform), match.platform)
            query = """ INSERT INTO lol_messages
                        (message_id, channel_id, match_id, champ_id) 
                        VALUES ($1, $2, $3, $4)
                    """
            await self.bot.pool.execute(query, msg.id, ch.id, match.match_id, match.champ_id)

    async def declare_matches_finished(self):
        query = """ UPDATE lol_matches 
                    SET is_finished=TRUE
                    WHERE NOT id=ANY($1)
                    AND lol_matches.is_finished IS DISTINCT FROM TRUE
                """
        await self.bot.pool.execute(query, self.all_live_match_ids)

    @tasks.loop(seconds=59)
    async def lolfeed_notifs(self):
        log.debug(f'LF | --- Task is starting now ---')
        await self.fill_live_matches()
        for match in self.live_matches:
            await self.send_notifications(match)
        await self.declare_matches_finished()
        log.debug(f'LF | --- Task is finished ---')

    @lolfeed_notifs.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @lolfeed_notifs.error
    async def lolfeed_notifs_error(self, error):
        await self.bot.send_traceback(error, where='LoLFeed Notifs')
        # self.lolfeed.restart()


class LoLFeedPostMatchEdits(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
        self.postmatch_players: List[PostMatchPlayer] = []
        self.postmatch_edits.start()

    async def fill_postmatch_players(self):
        """Fill `self.postmatch_players` -  data about players who have just finished their matches"""
        self.postmatch_players = []

        query = "SELECT * FROM lol_matches WHERE is_finished=TRUE"
        for row in await self.bot.pool.fetch(query):
            try:
                match = await lol.Match(
                    id=f'{row.platform.upper()}_{row.id}', region=row.region
                ).get()
            except NotFound:
                continue
            except ValueError as e:  # gosu incident ValueError: '' is not a valid platform
                print(e)
                continue  # TODO: remove message from the database

            query = 'SELECT * FROM lol_messages WHERE match_id=$1'
            for r in await self.bot.pool.fetch(query, row.id):
                for participant in match.info.participants:
                    if participant.champion_id == r.champ_id:
                        self.postmatch_players.append(
                            PostMatchPlayer(
                                player_data=participant,
                                channel_id=r.channel_id,
                                message_id=r.message_id,
                            )
                        )
                        query = 'UPDATE lol_accounts SET last_edited=$1 WHERE id=$2'
                        await self.bot.pool.execute(query, match.id, participant.summoner_id)
            query = 'DELETE FROM lol_matches WHERE id=$1'
            await self.bot.pool.fetch(query, row.id)

    @tasks.loop(seconds=59)
    async def postmatch_edits(self):
        #log.debug(f'LE | --- Task is starting now ---')
        await self.fill_postmatch_players()
        for player in self.postmatch_players:
            await player.edit_the_embed(self.bot)
        #log.debug(f'LE | --- Task is finished ---')

    @postmatch_edits.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @postmatch_edits.error
    async def postmatch_edits_error(self, error):
        await self.bot.send_traceback(error, where='LoLFeed PostMatchEdits')
        # self.lolfeed.restart()


class AddStreamFlags(commands.FlagConverter, case_insensitive=True):
    name: str
    server: LiteralServer
    account: str


class RemoveStreamFlags(commands.FlagConverter, case_insensitive=True):
    name: str
    server: Optional[LiteralServer]
    account: Optional[str]


class LoLFeedTools(commands.Cog, FPCBase, name='LoL'):
    """
    Commands to set up fav champ + fav stream notifs.

    These commands allow you to choose streamers from our database as your favorite \
    (or you can request adding them if they are missing) and choose your favorite League of Legends champions \
    The bot will send messages in a chosen channel when your fav streamer picks your fav champ.
    """

    def __init__(self, bot: AluBot):
        super().__init__(
            feature_name='LoLFeed',
            game_name='LoL',
            game_codeword='lol',
            colour=Clr.rspbrry,
            bot=bot,
            players_table='lol_players',
            accounts_table='lol_accounts',
            channel_id_column='lolfeed_ch_id',
            players_column='lolfeed_stream_ids',
            characters_column='lolfeed_champ_ids',
            spoil_column='lolfeed_spoils_on',
            acc_info_columns=['platform', 'account'],
            get_char_name_by_id=champion.name_by_id,
            get_char_id_by_name=champion.id_by_name,
            get_all_character_names=get_all_champ_names,
            character_gather_word='champs'
        )
        self.bot: AluBot = bot
        self.help_emote = Ems.PogChampPepe

    async def cog_load(self) -> None:
        await self.bot.ini_twitch()

    slh_lol = app_commands.Group(
        name="lol",
        description="Group command about LolFeed",
        default_permissions=Permissions(administrator=True)
    )

    @is_guild_owner()
    @commands.group(name='lol', aliases=['league'])
    async def ext_lol(self, ctx: Context):
        """Group command about LoL, for actual commands use it together with subcommands"""
        await ctx.scnf()

    slh_lol_channel = app_commands.Group(
        name='channel',
        description='Group command about LoLFeed channel settings',
        default_permissions=Permissions(administrator=True),
        parent=slh_lol
    )

    @is_guild_owner()
    @ext_lol.group()
    async def ext_lol_channel(self, ctx: Context):
        """Group command about LoL channel, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @is_guild_owner()
    @slh_lol_channel.command(
        name='set',
        description="Set channel to be the LoLFeed notifications channel"
    )
    @app_commands.describe(channel='Choose channel to set up LoLFeed notifications')
    async def slh_lol_channel_set(self, ntr: Interaction, channel: Optional[TextChannel] = None):
        """Slash copy of ext_lol_channel_set below"""
        ctx = await Context.from_interaction(ntr)
        await self.channel_set(ctx, channel)

    @is_guild_owner()
    @ext_lol_channel.command(name='set', usage='[channel=curr]')
    async def ext_lol_channel_set(self, ctx: Context, channel: Optional[TextChannel] = None):
        """Set channel to be the LoLFeed notifications channel."""
        await self.channel_set(ctx, channel)

    @slh_lol_channel.command(
        name='disable',
        description="Disable LoLFeed notifications channel"
    )
    async def slh_lol_channel_disable(self, ntr: Interaction):
        """Slash copy of ext_lol_channel_disable below"""
        ctx = await Context.from_interaction(ntr)
        await self.channel_disable(ctx)

    @is_guild_owner()
    @ext_lol_channel.command(name='disable')
    async def ext_lol_channel_disable(self, ctx: Context):
        """Stop getting LoLFeed notifs. Data about fav champs/players won't be affected."""
        await self.channel_disable(ctx)

    @is_guild_owner()
    @slh_lol_channel.command(
        name='check',
        description="Check if LoLFeed channel is set up"
    )
    async def slh_lol_channel_check(self, ntr: Interaction):
        """Slash copy of ext_lol_channel_check below"""
        ctx = await Context.from_interaction(ntr)
        await self.channel_check(ctx)

    @is_guild_owner()
    @ext_lol_channel.command(name='check')
    async def ext_lol_channel_check(self, ctx: Context):
        """Check if LoLFeed channel is set up in the server."""
        await self.channel_check(ctx)

    slh_lol_database = app_commands.Group(
        name='database',
        description='Group command about LoLFeed database',
        default_permissions=Permissions(administrator=True),
        parent=slh_lol
    )

    @is_guild_owner()
    @ext_lol.group(name='database', aliases=['db'])
    async def ext_lol_database(self, ctx: Context):
        """Group command about LoL database, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @staticmethod
    def player_acc_string(**kwargs):
        platform = kwargs.pop('platform')
        account = kwargs.pop('account')
        return f"`{platform_to_server(platform).upper()}` - `{account}`| {Account(platform, account).links}"

    @is_guild_owner()
    @slh_lol_database.command(
        name='list',
        description='List of players in the database available for LoLFeed feature'
    )
    async def slh_lol_database_list(self, ntr: Interaction):
        """Slash copy of ext_lol_database_list below"""
        ctx = await Context.from_interaction(ntr)
        await self.database_list(ctx)

    @is_guild_owner()
    @ext_lol_database.command(name='list')
    async def ext_lol_database_list(self, ctx: Context):
        """List of players in the database available for LoLFeed feature."""
        await self.database_list(ctx)

    @staticmethod
    async def get_lol_id(server: LiteralServer, account: str) -> (int, str, str):
        try:
            platform = server_to_platform(server)
            summoner = await lol.summoner.Summoner(name=account, platform=platform).get()
            return summoner.id, summoner.platform, summoner.name
        except NotFound:
            raise commands.BadArgument(
                f"Error checking league account with name `{account}` for `{server}` server: \n"
                f"This account does not exist."
            )

    async def get_account_dict(self, *, server: LiteralServer, account: str) -> dict:
        lol_id, platform, account = await self.get_lol_id(server, account)
        return {'id': lol_id, 'platform': platform, 'account': account}

    @is_trustee()
    @slh_lol_database.command(
        name='add',
        description='Add player to the database.'
    )
    @app_commands.describe(
        name='twitch.tv player\'s handle',
        server='Server of the account, i.e. "NA", "EUW"',
        account='Summoner name of the account'
    )
    async def slh_lol_database_add(self, ntr: Interaction, name: str, server: LiteralServerUpper, account: str):
        """Slash copy of ext_lol_database_list below"""
        ctx = await Context.from_interaction(ntr)
        await ctx.typing()
        player_dict = await self.get_player_dict(name_flag=name, twitch_flag=True)
        account_dict = await self.get_account_dict(server=server, account=account)
        await self.database_add(ctx, player_dict, account_dict)

    @is_trustee()
    @ext_lol_database.command(
        name='add',
        usage='name: <twitch_name> server: <server-region> account: <account_name>',
    )
    async def ext_lol_database_add(self, ctx: Context, *, flags: AddStreamFlags):
        """
        Add stream to the database.
        • `<name>` is twitch.tv stream name
        • `<server>` is LoL server/region of the account like NA, EUW
        • `<account>` is Summoner name of the account
        """
        await ctx.typing()
        player_dict = await self.get_player_dict(name_flag=flags.name, twitch_flag=True)
        account_dict = await self.get_account_dict(server=flags.server, account=flags.account)
        await self.database_add(ctx, player_dict, account_dict)

    @is_guild_owner()
    @slh_lol_database.command(
        name='request',
        description='Request player to be added into the database.'
    )
    @app_commands.describe(
        name='twitch.tv player\'s handle',
        server='Server of the account, i.e. "NA", "EUW"',
        account='Summoner name of the account'
    )
    async def slh_lol_database_request(self, ntr: Interaction, name: str, server: LiteralServerUpper, account: str):
        """Slash copy of ext_lol_database_request below"""
        ctx = await Context.from_interaction(ntr)
        await ctx.typing()
        player_dict = await self.get_player_dict(name_flag=name, twitch_flag=True)
        account_dict = await self.get_account_dict(server=server, account=account)
        await self.database_request(ctx, player_dict, account_dict)

    @is_guild_owner()
    @ext_lol_database.command(
        name='request',
        usage='name: <twitch_name> server: <server-region> account: <account_name>',
    )
    async def ext_lol_database_request(self, ctx: Context, *, flags: AddStreamFlags):
        """
        Request player to be added into the database. \
        This will send a request message into Aluerie's personal logs channel.
        """
        await ctx.typing()
        player_dict = await self.get_player_dict(name_flag=flags.name, twitch_flag=True)
        account_dict = await self.get_account_dict(server=flags.server, account=flags.account)
        await self.database_request(ctx, player_dict, account_dict)

    @is_trustee()
    @slh_lol_database.command(
        name='remove',
        description='Remove account/player from the database'
    )
    @app_commands.describe(
        name='Twitch.tv player name',
        server='Server region of the account',
        account='Summoner name of the account'
    )
    async def slh_lol_database_remove(
            self,
            ntr: Interaction,
            name: str,
            server: Optional[LiteralServerUpper],
            account: Optional[str]):
        """Slash copy of ext_lol_database_remove below"""
        ctx = await Context.from_interaction(ntr)
        await ctx.typing()
        if bool(server) != bool(account):
            raise commands.BadArgument('You need to provide both `server` and `account` to delete the specific account')
        elif server:
            lol_id, _, _ = self.get_lol_id(server=server, account=account)
        else:
            lol_id = None
        await self.database_remove(ctx, name.lower(), lol_id)

    @is_trustee()
    @ext_lol_database.command(
        name='remove',
        usage='name: <twitch_name> server: [Server region] account: [account_name]'
    )
    async def ext_lol_database_remove(self, ctx: Context, *, flags: RemoveStreamFlags):
        """Remove player from the database."""
        await ctx.typing()
        if bool(flags.server) != bool(flags.account):
            raise commands.BadArgument('You need to provide both `server` and `account` to delete the specific account')
        elif flags.server:
            lol_id, _, _ = self.get_lol_id(server=flags.server, account=flags.account)
        else:
            lol_id = None
        await self.database_remove(ctx, flags.name.lower(), lol_id)

    slh_lol_player = app_commands.Group(
        name='player',
        description='Group command about LoLFeed player',
        default_permissions=Permissions(administrator=True),
        parent=slh_lol
    )

    @is_guild_owner()
    @ext_lol.group(name='player', aliases=['streamer'])
    async def ext_lol_player(self, ctx: Context):
        """Group command about LoL player, for actual commands use it together with subcommands"""
        await ctx.scnf()

    async def lol_player_add_autocomplete(self, ntr: Interaction, current: str) -> List[app_commands.Choice[str]]:
        return await self.player_add_remove_autocomplete(ntr, current, mode_add=True)

    @is_guild_owner()
    @slh_lol_player.command(name='add', description='Add player to your favourites')
    @app_commands.describe(
        **{
            f'name{i}': 'Name of a player. Suggestions from database above exclude your already fav players'
            for i in range(1, 11)
        }
    )
    @app_commands.autocomplete(
        name1=lol_player_add_autocomplete,  # type: ignore
        name2=lol_player_add_autocomplete,  # type: ignore
        name3=lol_player_add_autocomplete,  # type: ignore
        name4=lol_player_add_autocomplete,  # type: ignore
        name5=lol_player_add_autocomplete,  # type: ignore
        name6=lol_player_add_autocomplete,  # type: ignore
        name7=lol_player_add_autocomplete,  # type: ignore
        name8=lol_player_add_autocomplete,  # type: ignore
        name9=lol_player_add_autocomplete,  # type: ignore
        name10=lol_player_add_autocomplete  # type: ignore
    )
    # @app_commands.autocomplete(**{f'name{i}': player_add_autocomplete for i in range(1, 11)})
    async def slh_lol_player_add(
            self, ntr: Interaction,
            name1: str, name2: str = None, name3: str = None, name4: str = None, name5: str = None,
            name6: str = None, name7: str = None, name8: str = None, name9: str = None, name10: str = None
    ):
        """Slash copy of ext_lol_player_add below"""
        player_names = list(set([
            name for name in list(locals().values())[2:] if name is not None
        ]))
        ctx = await Context.from_interaction(ntr)
        await self.player_add_remove(ctx, player_names, mode_add=True)

    @is_guild_owner()
    @ext_lol_player.command(name='add', usage='<player_name(-s)>')
    async def ext_lol_player_add(self, ctx: Context, *, player_names: str):
        """Add player to your favourites."""
        player_names = [x.lstrip().rstrip() for x in player_names.split(',') if x]
        await self.player_add_remove(ctx, player_names, mode_add=True)

    async def player_remove_autocomplete(self, ntr: Interaction, current: str) -> List[app_commands.Choice[str]]:
        return await self.player_add_remove_autocomplete(ntr, current, mode_add=False)

    @is_guild_owner()
    @slh_lol_player.command(name='remove', description='Remove player from your favourites')
    @app_commands.describe(**{f'name{i}': 'Name of a player' for i in range(1, 11)})
    @app_commands.autocomplete(
        name1=player_remove_autocomplete,  # type: ignore
        name2=player_remove_autocomplete,  # type: ignore
        name3=player_remove_autocomplete,  # type: ignore
        name4=player_remove_autocomplete,  # type: ignore
        name5=player_remove_autocomplete,  # type: ignore
        name6=player_remove_autocomplete,  # type: ignore
        name7=player_remove_autocomplete,  # type: ignore
        name8=player_remove_autocomplete,  # type: ignore
        name9=player_remove_autocomplete,  # type: ignore
        name10=player_remove_autocomplete  # type: ignore
    )
    # @app_commands.autocomplete(**{f'name{i}': player_remove_autocomplete for i in range(1, 11)})
    async def slh_lol_player_remove(
            self, ntr: Interaction,
            name1: str, name2: str = None, name3: str = None, name4: str = None, name5: str = None,
            name6: str = None, name7: str = None, name8: str = None, name9: str = None, name10: str = None
    ):
        """Slash copy of ext_lol_player_remove below"""
        player_names = list(set([
            name for name in list(locals().values())[2:] if name is not None
        ]))
        ctx = await Context.from_interaction(ntr)
        await self.player_add_remove(ctx, player_names, mode_add=False)

    @is_guild_owner()
    @ext_lol_player.command(name='remove', usage='<player_name(-s)>')
    async def ext_lol_player_remove(self, ctx: Context, *, player_names: str):
        """Add player to your favourites."""
        player_names = [x.lstrip().rstrip() for x in player_names.split(',') if x]
        await self.player_add_remove(ctx, player_names, mode_add=False)

    @is_guild_owner()
    @slh_lol_player.command(name='list', description='Show list of your favourite players')
    async def slh_lol_player_list(self, ntr: Interaction):
        """Slash copy of ext_lol_player below"""
        ctx = await Context.from_interaction(ntr)
        await self.player_list(ctx)

    @is_guild_owner()
    @ext_lol_player.command(name='list')
    async def ext_lol_player_list(self, ctx: Context):
        """Show current list of fav players."""
        await self.player_list(ctx)

    slh_lol_champ = app_commands.Group(
        name='champ',
        description='Group command about LoLFeed champs',
        default_permissions=Permissions(administrator=True),
        parent=slh_lol
    )

    @is_guild_owner()
    @ext_lol.group(name='champ')
    async def ext_lol_champ(self, ctx: Context):
        """Group command about LoL champs, for actual commands use it together with subcommands"""
        await ctx.scnf()

    async def lol_champ_add_autocomplete(self, ntr: Interaction, current: str) -> List[app_commands.Choice[str]]:
        return await self.character_add_remove_autocomplete(ntr, current, mode_add=True)

    @is_guild_owner()
    @slh_lol_champ.command(name='add', description='Add champ to your favourites')
    @app_commands.describe(**{f'name{i}': 'Name of a champ' for i in range(1, 11)})
    @app_commands.autocomplete(
        name1=lol_champ_add_autocomplete,  # type: ignore
        name2=lol_champ_add_autocomplete,  # type: ignore
        name3=lol_champ_add_autocomplete,  # type: ignore
        name4=lol_champ_add_autocomplete,  # type: ignore
        name5=lol_champ_add_autocomplete,  # type: ignore
        name6=lol_champ_add_autocomplete,  # type: ignore
        name7=lol_champ_add_autocomplete,  # type: ignore
        name8=lol_champ_add_autocomplete,  # type: ignore
        name9=lol_champ_add_autocomplete,  # type: ignore
        name10=lol_champ_add_autocomplete  # type: ignore
    )
    # @app_commands.autocomplete(**{f'name{i}': lol_champ_add_autocomplete for i in range(1, 11)})
    async def slh_lol_champ_add(
            self, ntr: Interaction,
            name1: str, name2: str = None, name3: str = None, name4: str = None, name5: str = None,
            name6: str = None, name7: str = None, name8: str = None, name9: str = None, name10: str = None
    ):
        """Slash copy of ext_lol_champ_add below"""
        champ_names = list(set([
            name for name in list(locals().values())[2:] if name is not None
        ]))
        ctx = await Context.from_interaction(ntr)
        await self.character_add_remove(ctx, champ_names, mode_add=True)

    @is_guild_owner()
    @ext_lol_champ.command(name='add', usage='<champ_name(-s)>',)
    async def ext_lol_champ_add(self, ctx: Context, *, champ_names: str):
        """Add champ(-es) to your fav champ list."""
        champ_names = [x.lstrip().rstrip() for x in champ_names.split(',') if x]
        await self.character_add_remove(ctx, champ_names, mode_add=True)

    async def lol_champ_remove_autocomplete(self, ntr: Interaction, current: str) -> List[app_commands.Choice[str]]:
        return await self.character_add_remove_autocomplete(ntr, current, mode_add=False)

    @is_guild_owner()
    @slh_lol_champ.command(name='remove', description='Remove champ from your favourites')
    @app_commands.describe(**{f'name{i}': 'Name of a champ' for i in range(1, 11)})
    @app_commands.autocomplete(
        name1=lol_champ_remove_autocomplete,  # type: ignore
        name2=lol_champ_remove_autocomplete,  # type: ignore
        name3=lol_champ_remove_autocomplete,  # type: ignore
        name4=lol_champ_remove_autocomplete,  # type: ignore
        name5=lol_champ_remove_autocomplete,  # type: ignore
        name6=lol_champ_remove_autocomplete,  # type: ignore
        name7=lol_champ_remove_autocomplete,  # type: ignore
        name8=lol_champ_remove_autocomplete,  # type: ignore
        name9=lol_champ_remove_autocomplete,  # type: ignore
        name10=lol_champ_remove_autocomplete  # type: ignore
    )
    # @app_commands.autocomplete(**{f'name{i}': lol_champ_add_autocomplete for i in range(1, 11)})
    async def slh_lol_champ_remove(
            self, ntr: Interaction,
            name1: str, name2: str = None, name3: str = None, name4: str = None, name5: str = None,
            name6: str = None, name7: str = None, name8: str = None, name9: str = None, name10: str = None
    ):
        """Slash copy of ext_lol_champ_remove below"""
        champ_names = list(set([
            name for name in list(locals().values())[2:] if name is not None
        ]))
        ctx = await Context.from_interaction(ntr)
        await self.character_add_remove(ctx, champ_names, mode_add=False)

    @is_guild_owner()
    @ext_lol_champ.command(name='remove', usage='<champ_name(-s)>')
    async def ext_lol_champ_remove(self, ctx: Context, *, champ_names: str):
        """Remove champ(-es) from your fav champs list."""
        champ_names = [x.lstrip().rstrip() for x in champ_names.split(',') if x]
        await self.character_add_remove(ctx, champ_names, mode_add=False)

    @is_guild_owner()
    @slh_lol_champ.command(name='list', description="Show your favourite champs list")
    async def slh_lol_champ_list(self, ntr: Interaction):
        """Slash copy of ext_lol_champ_list below"""
        ctx = await Context.from_interaction(ntr)
        await self.character_list(ctx)

    @is_guild_owner()
    @ext_lol_champ.command(name='list')
    async def ext_lol_champ_list(self, ctx: Context):
        """Show current list of fav champ."""
        await self.character_list(ctx)

    @is_guild_owner()
    @slh_lol.command(name='spoil', description="Turn on/off spoiling resulting stats for matches")
    @app_commands.describe(spoil='`Yes` to enable spoiling with stats, `No` for disable')
    async def slh_lol_spoil(self, ntr: Interaction, spoil: bool):
        """Slash copy of ext_lol_spoil below"""
        ctx = await Context.from_interaction(ntr)
        await self.spoil(ctx, spoil)

    @is_guild_owner()
    @ext_lol.command(name='spoil')
    async def ext_lol_spoil(self, ctx: Context, spoil: bool):
        """
        Turn on/off spoiling resulting stats for matches.
        It is "on" by default, so it can show what items players finished with and KDA.
        """
        await self.spoil(ctx, spoil)

    @is_owner()
    @ext_lol_champ.command()
    async def meraki(self, ctx: Context):
        """Show list of champions that are missing from Meraki JSON."""
        meraki_data = pull_data()
        champ_ids = await get_diff_list(meraki_data)
        champ_str = [
            f'● {await champion.key_by_id(i)} - `{i}`'
            for i in champ_ids
        ] or ['None missing']

        url_json = 'http://cdn.merakianalytics.com/riot/lol/resources/latest/en-US/championrates.json'
        async with self.bot.session.get(url_json) as resp:
            json_dict = await resp.json()
            meraki_patch = json_dict["patch"]

        em = Embed(title='List of champs missing from Meraki JSON', colour=Clr.rspbrry)
        em.description = '\n'.join(champ_str)
        em.add_field(
            name='Links',
            value=(
                f'• [GitHub](https://github.com/meraki-analytics/role-identification)\n'
                f'• [Json]({url_json})'
            )
        )
        em.add_field(name='Meraki last updated', value=f'Patch {meraki_patch}')
        await ctx.reply(embed=em)


class LoLAccCheck(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
        self.check_acc_renames.start()

    def cog_unload(self) -> None:
        self.check_acc_renames.cancel()

    @tasks.loop(time=time(hour=12, minute=11, tzinfo=timezone.utc))
    async def check_acc_renames(self):
        log.info("league checking acc renames every 24 hours")
        query = 'SELECT id, platform, accname FROM lolaccs'
        rows = await self.bot.pool.fetch(query)

        for row in rows:
            person = await lol.summoner.Summoner(id=row.id, platform=row.platform).get()
            if person.name != row.accname:
                query = 'UPDATE lolaccs SET accname=$1 WHERE id=$2'
                await self.bot.pool.execute(query, person.name, row.id)

    @check_acc_renames.before_loop
    async def before(self):
        log.info("check_acc_renames before the loop")
        await self.bot.wait_until_ready()


async def setup(bot: AluBot):
    await bot.add_cog(LoLFeedNotifications(bot))
    await bot.add_cog(LoLFeedPostMatchEdits(bot))
    await bot.add_cog(LoLFeedTools(bot))
    if datetime.now(timezone.utc).day == 17:
        await bot.add_cog(LoLAccCheck(bot))
