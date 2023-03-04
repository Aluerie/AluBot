from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional, Tuple

import discord
from discord import app_commands
from discord.ext import commands
from pyot.core.exceptions import NotFound
from pyot.utils.lol import champion

from utils.checks import is_manager
from utils.lol.const import LOL_LOGO, LiteralServer, LiteralServerUpper, platform_to_server, server_to_platform
from utils.lol.utils import get_all_champ_names, get_meraki_patch, get_pyot_meraki_champ_diff_list
from utils.var import Clr, Ems

from .._base import FPCBase
from ._models import Account

# need to import the last because in import above we activate 'lol' model
from pyot.models import lol  # isort: skip

if TYPE_CHECKING:
    from utils.bot import AluBot
    from utils.context import Context

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class AddStreamFlags(commands.FlagConverter, case_insensitive=True):
    name: str
    server: LiteralServer
    account: str


class RemoveStreamFlags(commands.FlagConverter, case_insensitive=True):
    name: str
    server: Optional[LiteralServer]
    account: Optional[str]


class LoLNotifsSettings(commands.Cog, FPCBase, name='LoL'):
    """Commands to set up fav champ + fav stream notifs.

    These commands allow you to choose streamers from our database as your favorite \
    (or you can request adding them if they are missing) and choose your favorite League of Legends champions \
    The bot will send messages in a chosen channel when your fav streamer picks your fav champ.
    """

    def __init__(self, bot: AluBot):
        super().__init__(
            feature_name='LoLFeed',
            game_name='LoL',
            game_codeword='lol',
            game_logo=LOL_LOGO,
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
            character_gather_word='champs',
        )
        self.bot: AluBot = bot

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(Ems.PogChampPepe)

    async def cog_load(self) -> None:
        await self.bot.ini_twitch()

    # lol ##############################################

    slh_lol = app_commands.Group(
        name="lol",
        description="Group command about LolFeed",
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @is_manager()
    @commands.group(name='lol', aliases=['league'])
    async def ext_lol(self, ctx: Context):
        """Group command about LoL, for actual commands use it together with subcommands"""
        await ctx.scnf()

    # lol channel ##############################################

    slh_lol_channel = app_commands.Group(
        name='channel', description='Group command about LoLFeed channel settings', parent=slh_lol
    )

    @is_manager()
    @ext_lol.group()
    async def ext_lol_channel(self, ctx: Context):
        """Group command about LoL channel, for actual commands use it together with subcommands"""
        await ctx.scnf()

    # lol channel set ##############################################

    @slh_lol_channel.command(name='set')
    @app_commands.describe(channel='Choose channel to set up LoLFeed notifications')
    async def slh_lol_channel_set(
        self, ntr: discord.Interaction[AluBot], channel: Optional[discord.TextChannel] = None
    ):
        """Set channel to be the LoLFeed notifications channel."""
        await self.channel_set(ntr, channel)

    @is_manager()
    @ext_lol_channel.command(name='set', usage='[channel=curr]')
    async def ext_lol_channel_set(self, ctx: Context, channel: Optional[discord.TextChannel] = None):
        """Set channel to be the LoLFeed notifications channel."""
        await self.channel_set(ctx, channel)

    # lol channel disable ##############################################

    @slh_lol_channel.command(name='disable')
    async def slh_lol_channel_disable(self, ntr: discord.Interaction[AluBot]):
        """Disable LoLFeed notifications channel."""
        await self.channel_disable(ntr)

    @is_manager()
    @ext_lol_channel.command(name='disable')
    async def ext_lol_channel_disable(self, ctx: Context):
        """Stop getting LoLFeed notifs. Data about fav champs/players won't be affected."""
        await self.channel_disable(ctx)

    # lol channel check ##############################################

    @slh_lol_channel.command(name='check')
    async def slh_lol_channel_check(self, ntr: discord.Interaction[AluBot]):
        """Check if LoLFeed channel is set up."""
        await self.channel_check(ntr)

    @is_manager()
    @ext_lol_channel.command(name='check')
    async def ext_lol_channel_check(self, ctx: Context):
        """Check if LoLFeed channel is set up in the server."""
        await self.channel_check(ctx)

    # lol database ##############################################

    slh_lol_database = app_commands.Group(
        name='database',
        description='Group command about LoLFeed database',
        parent=slh_lol,
    )

    @is_manager()
    @ext_lol.group(name='database', aliases=['db'])
    async def ext_lol_database(self, ctx: Context):
        """Group command about LoL database, for actual commands use it together with subcommands"""
        await ctx.scnf()

    # helper functions ##############################################

    @staticmethod
    def cmd_usage_str(**kwargs):
        platform = kwargs.pop('platform')
        account = kwargs.pop('account')
        return f'server: {platform_to_server(platform).upper()} account: {account}'

    @staticmethod
    def player_acc_string(**kwargs):
        platform = kwargs.pop('platform')
        account = kwargs.pop('account')
        return f"`{platform_to_server(platform).upper()}` - `{account}` {Account(platform, account).links}"

    @staticmethod
    async def get_lol_id(server: LiteralServer, account: str) -> Tuple[str, str, str]:
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

    # lol database list ##################################

    @slh_lol_database.command(name='list')
    async def slh_lol_database_list(self, ntr: discord.Interaction[AluBot]):
        """List of players in the database available for LoLFeed feature."""
        await self.database_list(ntr)

    @is_manager()
    @ext_lol_database.command(name='list')
    async def ext_lol_database_list(self, ctx: Context):
        """List of players in the database available for LoLFeed feature."""
        await self.database_list(ctx)

    # lol database request ##################################

    @slh_lol_database.command(name='request')
    @app_commands.describe(
        name='twitch.tv player\'s handle',
        server='Server of the account, i.e. "NA", "EUW"',
        account='Summoner name of the account',
    )
    async def slh_lol_database_request(
        self, ntr: discord.Interaction[AluBot], name: str, server: LiteralServerUpper, account: str
    ):
        """Request player to be added into the database."""
        player_dict = await self.get_player_dict(name_flag=name, twitch_flag=True)
        account_dict = await self.get_account_dict(server=server, account=account)
        await self.database_request(ntr, player_dict, account_dict)

    @is_manager()
    @ext_lol_database.command(
        name='request',
        usage='name: <twitch_name> server: <server-region> account: <account_name>',
    )
    async def ext_lol_database_request(self, ctx: Context, *, flags: AddStreamFlags):
        """Request player to be added into the database.
        This will send a request message into Aluerie's personal logs channel.
        """
        player_dict = await self.get_player_dict(name_flag=flags.name, twitch_flag=True)
        account_dict = await self.get_account_dict(server=flags.server, account=flags.account)
        await self.database_request(ctx, player_dict, account_dict)

    # lol player ##################################

    slh_lol_player = app_commands.Group(
        name='player',
        description='Group command about LoLFeed player',
        parent=slh_lol,
    )

    @is_manager()
    @ext_lol.group(name='player', aliases=['streamer'])
    async def ext_lol_player(self, ctx: Context):
        """Group command about LoL player, for actual commands use it together with subcommands"""
        await ctx.scnf()

    # lol player add ##################################

    async def lol_player_add_autocomplete(
        self, ntr: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return await self.player_add_remove_autocomplete(ntr, current, mode_add=True)

    @slh_lol_player.command(name='add')
    @app_commands.describe(
        **{
            f'name{i}': 'Name of a player. Suggestions from database above exclude your already fav players'
            for i in range(1, 11)
        }
    )
    @app_commands.autocomplete(
        name1=lol_player_add_autocomplete,
        name2=lol_player_add_autocomplete,
        name3=lol_player_add_autocomplete,
        name4=lol_player_add_autocomplete,
        name5=lol_player_add_autocomplete,
        name6=lol_player_add_autocomplete,
        name7=lol_player_add_autocomplete,
        name8=lol_player_add_autocomplete,
        name9=lol_player_add_autocomplete,
        name10=lol_player_add_autocomplete,
    )
    # @app_commands.autocomplete(**{f'name{i}': player_add_autocomplete for i in range(1, 11)})
    async def slh_lol_player_add(
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
    @ext_lol_player.command(name='add', usage='<player_name(-s)>')
    async def ext_lol_player_add(self, ctx: Context, *, player_names: str):
        """Add player to your favourites."""
        await self.player_add_remove(ctx, locals(), mode_add=True)

    # lol player remove ##################################

    async def player_remove_autocomplete(
        self, ntr: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return await self.player_add_remove_autocomplete(ntr, current, mode_add=False)

    @slh_lol_player.command(name='remove')
    @app_commands.describe(**{f'name{i}': 'Name of a player' for i in range(1, 11)})
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
    async def slh_lol_player_remove(
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
    @ext_lol_player.command(name='remove', usage='<player_name(-s)>')
    async def ext_lol_player_remove(self, ctx: Context, *, player_names: str):
        """Add player to your favourites."""
        await self.player_add_remove(ctx, locals(), mode_add=False)

    # lol player list ##################################

    @slh_lol_player.command(name='list')
    async def slh_lol_player_list(self, ntr: discord.Interaction[AluBot]):
        """Show list of your favourite players."""
        await self.player_list(ntr)

    @is_manager()
    @ext_lol_player.command(name='list')
    async def ext_lol_player_list(self, ctx: Context):
        """Show list of your favourite players."""
        await self.player_list(ctx)

    # lol champ ##################################

    slh_lol_champ = app_commands.Group(
        name='champ',
        description='Group command about LoLFeed champs',
        parent=slh_lol,
    )

    @is_manager()
    @ext_lol.group(name='champ')
    async def ext_lol_champ(self, ctx: Context):
        """Group command about LoL champs, for actual commands use it together with subcommands"""
        await ctx.scnf()

    # lol champ add ##################################

    async def lol_champ_add_autocomplete(
        self, ntr: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return await self.character_add_remove_autocomplete(ntr, current, mode_add=True)

    @slh_lol_champ.command(name='add')
    @app_commands.describe(**{f'name{i}': 'Name of a champ' for i in range(1, 11)})
    @app_commands.autocomplete(
        name1=lol_champ_add_autocomplete,
        name2=lol_champ_add_autocomplete,
        name3=lol_champ_add_autocomplete,
        name4=lol_champ_add_autocomplete,
        name5=lol_champ_add_autocomplete,
        name6=lol_champ_add_autocomplete,
        name7=lol_champ_add_autocomplete,
        name8=lol_champ_add_autocomplete,
        name9=lol_champ_add_autocomplete,
        name10=lol_champ_add_autocomplete,
    )
    # @app_commands.autocomplete(**{f'name{i}': lol_champ_add_autocomplete for i in range(1, 11)})
    async def slh_lol_champ_add(
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
        """Add champ to your favourites."""
        await self.character_add_remove(ntr, locals(), mode_add=True)

    @is_manager()
    @ext_lol_champ.command(
        name='add',
        usage='<champ_name(-s)>',
    )
    async def ext_lol_champ_add(self, ctx: Context, *, champ_names: str):
        """Add champ(-s) to your fav champ list."""
        await self.character_add_remove(ctx, locals(), mode_add=True)

    # lol champ remove ##################################

    async def lol_champ_remove_autocomplete(
        self, ntr: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return await self.character_add_remove_autocomplete(ntr, current, mode_add=False)

    @slh_lol_champ.command(name='remove')
    @app_commands.describe(**{f'name{i}': 'Name of a champ' for i in range(1, 11)})
    @app_commands.autocomplete(
        name1=lol_champ_remove_autocomplete,
        name2=lol_champ_remove_autocomplete,
        name3=lol_champ_remove_autocomplete,
        name4=lol_champ_remove_autocomplete,
        name5=lol_champ_remove_autocomplete,
        name6=lol_champ_remove_autocomplete,
        name7=lol_champ_remove_autocomplete,
        name8=lol_champ_remove_autocomplete,
        name9=lol_champ_remove_autocomplete,
        name10=lol_champ_remove_autocomplete,
    )
    # @app_commands.autocomplete(**{f'name{i}': lol_champ_add_autocomplete for i in range(1, 11)})
    async def slh_lol_champ_remove(
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
        """Remove champ from your favourites."""
        await self.character_add_remove(ntr, locals(), mode_add=False)

    @is_manager()
    @ext_lol_champ.command(name='remove', usage='<champ_name(-s)>')
    async def ext_lol_champ_remove(self, ctx: Context, *, champ_names: str):
        """Remove champ(-es) from your fav champs list."""
        await self.character_add_remove(ctx, locals(), mode_add=False)

    # lol champ list ##################################

    @slh_lol_champ.command(name='list')
    async def slh_lol_champ_list(self, ntr: discord.Interaction[AluBot]):
        """Show your favourite champs list."""
        await self.character_list(ntr)

    @is_manager()
    @ext_lol_champ.command(name='list')
    async def ext_lol_champ_list(self, ctx: Context):
        """Show current list of fav champ."""
        await self.character_list(ctx)

    # lol champ spoil ##################################

    @slh_lol.command(name='spoil')
    @app_commands.describe(spoil='`True` to enable spoiling with stats, `False` for disable')
    async def slh_lol_spoil(self, ntr: discord.Interaction[AluBot], spoil: bool):
        """Turn on/off spoiling resulting stats for matches."""
        await self.spoil(ntr, spoil)

    @is_manager()
    @ext_lol.command(name='spoil')
    async def ext_lol_spoil(self, ctx: Context, spoil: bool):
        """Turn on/off spoiling resulting stats for matches.
        It is "on" by default, so it can show what items players finished with and KDA.
        """
        await self.spoil(ctx, spoil)

    # meraki ##################################

    @commands.command(hidden=True)
    async def meraki(self, ctx: Context):
        """Show list of champions that are missing from Meraki JSON."""
        champ_ids = await get_pyot_meraki_champ_diff_list()
        champ_str = [f'\N{BLACK CIRCLE} {await champion.key_by_id(i)} - `{i}`' for i in champ_ids] or ['None missing']

        meraki_patch = await get_meraki_patch()

        e = discord.Embed(title='List of champs missing from Meraki JSON', colour=Clr.rspbrry)
        e.description = '\n'.join(champ_str)
        e.add_field(
            name='Links',
            value=(
                f'• [GitHub](https://github.com/meraki-analytics/role-identification)\n'
                f'• [Json](https://cdn.merakianalytics.com/riot/lol/resources/latest/en-US/championrates.json)'
            ),
        )
        e.add_field(name='Meraki last updated', value=f'Patch {meraki_patch}')
        await ctx.reply(embed=e)


async def setup(bot):
    await bot.add_cog(LoLNotifsSettings(bot))
